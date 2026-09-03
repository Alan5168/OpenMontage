from __future__ import annotations

import builtins
import importlib
import sys


def test_embedding_service_import_does_not_require_service_dependencies(monkeypatch) -> None:
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in {"flask", "sentence_transformers"}:
            raise AssertionError(f"optional dependency imported during registry discovery: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("tools.content_studio_embedding_service", None)
    module = importlib.import_module("tools.content_studio_embedding_service")

    assert module._texts_from_body({"text": "one"}) == ["one"]
    assert module._texts_from_body({"input": ["one", 2]}) == ["one", "2"]
