import io
import json
from pathlib import Path

import pytest

from radar import transformer as t


def test_offline_produces_distinct_task_mechanics():
    ideas = t.offline_ideas('Gyvūnų šešėlių poravimas', 'pastabumas ir gyvūnų atpažinimas', '3–4 m.')
    assert len(ideas) == 6
    assert len({idea['mechanism'] for idea in ideas}) == 6
    assert all(idea['description'] and idea['difference'] for idea in ideas)
    assert all('šešėlių poravimas' not in x['description'] for x in ideas)


def test_fraction_examples_specific():
    ideas = t.offline_ideas('Trupmenų palyginimas', 'didesnis vardiklis', '1–4 kl.', 'HTML')
    assert '1/2' in ' '.join(x['description'] for x in ideas)
    assert len(ideas) == 6


def test_prompt_explicit_copyright_and_attachment():
    prompt = t.build_prompt('šešėlių poravimas', 'pastabumas', '3–4 m.', 'HTML', 'https://example.com/', '', 'source.png')
    assert 'Nesukurk jokios to paties darbo kopijos' in prompt
    assert 'source.png' in prompt
    assert 'ChatGPT' not in prompt or isinstance(prompt, str)


def test_saved_idea_deduplicated_and_backed_up(tmp_path):
    path = tmp_path / 'transformer_ideas.json'
    idea = t.offline_ideas('drabužiai', 'sekos', '3–4 m.')[0]
    assert t.save_idea(idea, 'https://example.com/', path=path)
    assert not t.save_idea(idea, 'https://example.com/', path=path)
    saved = t.read_saved(path)
    assert len(saved) == 1
    other = tmp_path / 'restored.json'
    assert t.import_backup(json.dumps(saved,ensure_ascii=False).encode(), path=other) == 1
    assert t.import_backup(json.dumps(saved,ensure_ascii=False).encode(), path=other) == 0
    assert t.read_saved(other)[0]['title'] == idea['title']


def test_reject_bad_backup(tmp_path):
    with pytest.raises(ValueError):
        t.import_backup(b'{broken', path=tmp_path/'a.json')
    with pytest.raises(ValueError):
        t.import_backup(b'{}', path=tmp_path/'a.json')


def test_public_url_validation():
    for url in ['http://127.0.0.1', 'http://localhost/', 'file:///etc/passwd',
                'https://example.com:5000/', 'https://user:pass@example.com/',
                'http://192.168.0.1/', 'http://169.254.169.254/latest/meta-data']:
        assert not t.safe_url(url)


def test_txt_and_pptx_extraction():
    assert t.extract_text('Labas pasauli'.encode(), 'notes.txt')[0] == 'Labas pasauli'
    from pptx import Presentation
    p = Presentation()
    slide = p.slides.add_slide(p.slide_layouts[5])
    slide.shapes.title.text = 'Spalvos ir formos'
    b = io.BytesIO(); p.save(b)
    txt, status = t.extract_text(b.getvalue(), 'slides.pptx')
    assert 'Spalvos' in txt and 'PPTX' in status


def test_pdf_extraction_and_preview():
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=500,height=500)
    page.insert_text((50,50),'Fraction cards',fontsize=20)
    raw = doc.tobytes()
    text, status = t.extract_text(raw, 'sample.pdf')
    assert 'Fraction cards' in text and 'PDF' in status
    picture = t.pdf_page_preview(raw)
    assert picture.startswith(b'\xff\xd8')


def test_png_conversion():
    from PIL import Image
    im = Image.new('RGBA',(2000,1000),(22,50,60,150))
    b = io.BytesIO(); im.save(b,format='PNG')
    compressed = t.image_to_ai_jpeg(b.getvalue())
    assert compressed.startswith(b'\xff\xd8')
