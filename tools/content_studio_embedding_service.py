#!/usr/bin/env python3
"""Loopback Qwen3 embedding service for OpenViking and om_media_bridge.

Binds 127.0.0.1 only. Serves both:
  POST /v1/embeddings   OpenAI-compatible (OpenViking)
  POST /embed           simple {text|input} -> {embedding} (om_media_bridge)
  GET  /health
Default port 18889. CPU-only so H3/ComfyUI keep the GPU.
"""

from __future__ import annotations

import os
import sys
from typing import Any

MODEL_PATH = os.environ.get(
    "EMBEDDING_MODEL_PATH",
    r"C:\ContentStudio\models\Qwen3-Embedding-0.6B",
)
EMBEDDING_DIM = 1024
_model: Any | None = None


def _get_model() -> Any:
    global _model
    if _model is None:
        import torch
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(
            MODEL_PATH,
            device="cpu",
            model_kwargs={"torch_dtype": torch.bfloat16, "low_cpu_mem_usage": True},
        )
    return _model


def _texts_from_body(data: dict[str, Any]) -> list[str]:
    if data.get("text") is not None:
        texts = data["text"]
    elif data.get("input") is not None:
        texts = data["input"]
    else:
        texts = []
    if isinstance(texts, str):
        return [texts]
    if isinstance(texts, list):
        return [str(t) for t in texts]
    raise ValueError("input/text must be a string or list of strings")


def _encode(texts: list[str]) -> list[list[float]]:
    vectors = _get_model().encode(texts, normalize_embeddings=True)
    return [vec.tolist() for vec in vectors]


def create_app() -> Any:
    """Build the Flask app only when the embedding service is launched.

    Tool discovery imports every module below ``tools``. Keeping the optional
    service dependencies inside this factory prevents provider discovery from
    requiring the dedicated embedding virtualenv.
    """
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    @app.route("/v1/embeddings", methods=["POST"])
    def openai_embeddings():
        data = request.get_json(force=True, silent=True) or {}
        try:
            texts = _texts_from_body(data)
            if not texts:
                return jsonify({"error": "missing input"}), 400
            vectors = _encode(texts)
        except Exception as exc:
            return jsonify({"error": type(exc).__name__, "detail": str(exc)}), 500
        return jsonify(
            {
                "object": "list",
                "data": [
                    {"object": "embedding", "index": i, "embedding": vec}
                    for i, vec in enumerate(vectors)
                ],
                "model": "qwen3-embedding-0.6b",
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }
        )

    @app.route("/embed", methods=["POST"])
    def simple_embed():
        data = request.get_json(force=True, silent=True) or {}
        try:
            texts = _texts_from_body(data)
            if not texts:
                return jsonify({"error": "missing text"}), 400
            vectors = _encode(texts)
        except Exception as exc:
            return jsonify({"error": type(exc).__name__, "detail": str(exc)}), 500
        return jsonify(
            {
                "embedding": vectors[0],
                "embeddings": vectors,
                "vector": vectors[0],
                "model": "qwen3-embedding-0.6b",
                "dim": EMBEDDING_DIM,
            }
        )

    @app.route("/health", methods=["GET"])
    def health():
        ready = _model is not None
        payload = {
            "status": "ok" if ready else "loading",
            "model": "qwen3-embedding-0.6b",
            "dim": EMBEDDING_DIM,
            "bind": "127.0.0.1",
            "ready": ready,
        }
        return jsonify(payload), (200 if ready else 503)

    return app


def main() -> int:
    port = int(os.environ.get("EMBEDDING_SERVICE_PORT", "18889"))
    host = os.environ.get("EMBEDDING_BIND_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost"}:
        print("refusing non-loopback bind", file=sys.stderr)
        return 2
    # Warm the model before serving so OpenViking doctor is not racing lazy load.
    _get_model()
    app = create_app()
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
