"""Pruebas para la capa web POST (src/web.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import requests
import web


class FakeResp:
    def __init__(self, data=None, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}")

    def json(self):
        return self._data


def test_post_json_ok(monkeypatch):
    llamadas = []

    def _post(url, json=None, headers=None, timeout=60):
        llamadas.append((url, json, timeout))
        return FakeResp({"ok": True})

    monkeypatch.setattr(web.requests, "post", _post)
    assert web.post_json("https://ejemplo.com/x", {"a": 1}, timeout=120) == {"ok": True}
    assert llamadas[0] == ("https://ejemplo.com/x", {"a": 1}, 120)


def test_post_json_errores(monkeypatch):
    import pytest

    def _timeout(*a, **k):
        raise requests.exceptions.Timeout()
    monkeypatch.setattr(web.requests, "post", _timeout)
    with pytest.raises(web.WebError, match="tardó demasiado"):
        web.post_json("https://ejemplo.com/x", {})

    monkeypatch.setattr(web.requests, "post",
                        lambda *a, **k: FakeResp(status=500))
    with pytest.raises(web.WebError, match="HTTP 500"):
        web.post_json("https://ejemplo.com/x", {})
