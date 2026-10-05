"""Minimali streamlit imitacija UI smoke testui be streamlit diegimo."""
import sys, types, contextlib
from datetime import date


class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, n): return _fn(n)
    def __iter__(self): return iter([])


def _fn(name):
    def f(*a, **k):
        if name in ("columns",):
            n = a[0] if isinstance(a[0], int) else len(a[0]); return [_Ctx() for _ in range(n)]
        if name == "tabs": return [_Ctx() for _ in a[0]]
        if name in ("expander", "empty", "container", "spinner"): return _Ctx()
        if name == "radio": 
            o = a[1]; i = k.get("index", 0); return o[i]
        if name == "selectbox": return a[1][0]
        if name == "multiselect": return k.get("default", [])
        if name in ("checkbox", "button", "download_button"): return k.get("value", False) if name == "checkbox" else False
        if name == "slider": return a[3] if len(a) > 3 else 0
        if name == "text_input": return ""
        if name == "date_input": return k.get("value", date.today())
        if name == "file_uploader": return None
        if name == "progress": return _Ctx()
        return _Ctx()
    return f


class FakeSt(types.ModuleType):
    session_state = {}
    def __getattr__(self, n):
        if n == "sidebar": return _Ctx()
        if n == "cache_resource":
            def deco(*a, **k):
                if a and callable(a[0]): return a[0]
                return lambda fn: fn
            deco.clear = lambda: None
            return deco
        if n == "cache_data":
            return lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
        return _fn(n)


def install():
    m = FakeSt("streamlit"); sys.modules["streamlit"] = m; return m
