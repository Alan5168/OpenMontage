#!/usr/bin/env python3
"""CPU-only WeMM-Embedding-2B server for OpenViking multimodal memory and shadow index.

Must never see the GPU. CUDA_VISIBLE_DEVICES is cleared before torch import.
Default output is Matryoshka 1024-d L2-normalized vectors.
Binds 127.0.0.1 only.
"""

from __future__ import annotations

import base64
import io
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["HIP_VISIBLE_DEVICES"] = "-1"
os.environ["ROCR_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODEL_PATH = os.environ.get(
    "WEMM_MODEL_PATH",
    r"C:\ContentStudio\models\WeMM-Embedding-2B",
)
EMBEDDING_DIM = int(os.environ.get("WEMM_EMBEDDING_DIM", "1024"))
DEFAULT_TASK = os.environ.get("WEMM_DEFAULT_TASK", "document")
_model: Any | None = None


def _force_cpu() -> None:
    import torch

    if torch.cuda.is_available():
        raise RuntimeError(
            "WeMM service can see CUDA; refuse to start. "
            f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')!r}"
        )


def _get_model() -> Any:
    global _model
    if _model is None:
        import torch
        from sentence_transformers import SentenceTransformer

        _force_cpu()
        dtype = torch.bfloat16
        _model = SentenceTransformer(
            MODEL_PATH,
            trust_remote_code=True,
            device="cpu",
            model_kwargs={"torch_dtype": dtype, "low_cpu_mem_usage": True},
        )
        _force_cpu()
    return _model


def _load_image(img_ref: Any) -> Any:
    """Load image from PIL Image, file path, file:// URI, base64 data URI, or URL."""
    from PIL import Image

    if isinstance(img_ref, Image.Image):
        return img_ref.convert("RGB")

    if not isinstance(img_ref, str):
        raise ValueError(f"Unsupported image reference type: {type(img_ref)}")

    img_ref = img_ref.strip()

    # Base64 data URI (e.g. data:image/png;base64,...)
    if img_ref.startswith("data:image/") and ";base64," in img_ref:
        header, encoded = img_ref.split(";base64,", 1)
        raw = base64.b64decode(encoded)
        return Image.open(io.BytesIO(raw)).convert("RGB")

    # Raw base64 string without data: header
    if len(img_ref) > 256 and not img_ref.startswith(("http://", "https://", "file://", "C:", "/", "\\")):
        try:
            raw = base64.b64decode(img_ref)
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            pass

    # file:// URI
    if img_ref.startswith("file://"):
        parsed = urlparse(img_ref)
        local_path = unquote(parsed.path)
        if local_path.startswith("/") and len(local_path) > 2 and local_path[2] == ":":
            local_path = local_path[1:]
        return Image.open(local_path).convert("RGB")

    # Local file path
    p = Path(img_ref)
    if p.is_file():
        return Image.open(p).convert("RGB")

    # Remote HTTP/HTTPS URL
    if img_ref.startswith(("http://", "https://")):
        import urllib.request
        with urllib.request.urlopen(img_ref, timeout=10) as resp:
            data = resp.read()
            return Image.open(io.BytesIO(data)).convert("RGB")

    raise FileNotFoundError(f"Cannot resolve image from reference: {img_ref[:100]}...")


def _resolve_single_item(item: Any) -> Any:
    """Normalize a single content item (string, dict, or part) into WeMM input."""
    if isinstance(item, str):
        # Check if it is a local image file path
        if any(item.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
            p = Path(item)
            if p.is_file():
                return _load_image(p)
        return item

    if isinstance(item, dict):
        # OpenAI content part format: {"type": "text", "text": "..."} or {"type": "image_url", ...}
        if item.get("type") == "text":
            return str(item.get("text", ""))
        if item.get("type") == "image_url":
            img_url = item.get("image_url")
            url = img_url.get("url") if isinstance(img_url, dict) else img_url
            return _load_image(url)
        if item.get("image") is not None and item.get("text") is not None:
            return {"text": str(item["text"]), "image": _load_image(item["image"])}
        if item.get("image") is not None:
            return _load_image(item["image"])
        if item.get("text") is not None:
            return str(item["text"])

    if isinstance(item, list):
        # Multi-part content for a single embedding (e.g. list of parts from OpenViking)
        texts: list[str] = []
        images: list[Any] = []
        for part in item:
            resolved = _resolve_single_item(part)
            if isinstance(resolved, str):
                texts.append(resolved)
            elif hasattr(resolved, "convert"):  # PIL Image
                images.append(resolved)
            elif isinstance(resolved, dict):
                if "text" in resolved:
                    texts.append(resolved["text"])
                if "image" in resolved:
                    images.append(resolved["image"])

        combined_text = " ".join(t.strip() for t in texts if t.strip())
        if images and combined_text:
            return {"text": combined_text, "image": images[0]}
        if images:
            return images[0]
        if combined_text:
            return combined_text
        return ""

    return item


def _items_from_body(data: dict[str, Any]) -> list[Any]:
    if data.get("text") is not None:
        raw = data["text"]
    elif data.get("input") is not None:
        raw = data["input"]
    elif data.get("contents") is not None:
        raw = data["contents"]
    else:
        raw = []

    if isinstance(raw, (str, dict)):
        return [_resolve_single_item(raw)]

    if isinstance(raw, list):
        if not raw:
            return []
        # Check if raw is a single multi-part list (e.g. [{"type": "text"}, {"type": "image_url"}])
        if all(isinstance(x, dict) and ("type" in x or "image" in x or "text" in x) for x in raw):
            has_types = any("type" in x for x in raw)
            if has_types:
                return [_resolve_single_item(raw)]
        return [_resolve_single_item(x) for x in raw]

    raise ValueError("input/text/contents must be a string, dict, or list")


def _task(data: dict[str, Any]) -> str:
    raw = data.get("input_type") or data.get("task") or data.get("is_query") or DEFAULT_TASK
    if isinstance(raw, bool):
        return "query" if raw else "document"
    raw = str(raw).lower()
    if raw in {"query", "queries", "search", "true", "1"}:
        return "query"
    return "document"


def _encode(items: list[Any], task: str) -> list[list[float]]:
    model = _get_model()
    kwargs = {
        "truncate_dim": EMBEDDING_DIM,
        "normalize_embeddings": True,
        "show_progress_bar": False,
    }
    if task == "query":
        vectors = model.encode_query(items, **kwargs)
    else:
        vectors = model.encode_document(items, **kwargs)
    return [vec.tolist() for vec in vectors]


def create_app() -> Any:
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    @app.route("/v1/embeddings", methods=["POST"])
    def openai_embeddings():
        data = request.get_json(force=True, silent=True) or {}
        try:
            items = _items_from_body(data)
            if not items:
                return jsonify({"error": "missing input"}), 400
            task = _task(data)
            vectors = _encode(items, task)
        except Exception as exc:
            return jsonify({"error": type(exc).__name__, "detail": str(exc)}), 500
        return jsonify(
            {
                "object": "list",
                "data": [
                    {"object": "embedding", "index": i, "embedding": vec}
                    for i, vec in enumerate(vectors)
                ],
                "model": "wemm-embedding-2b",
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }
        )

    @app.route("/embed", methods=["POST"])
    def simple_embed():
        data = request.get_json(force=True, silent=True) or {}
        try:
            items = _items_from_body(data)
            if not items:
                return jsonify({"error": "missing text"}), 400
            task = _task(data)
            vectors = _encode(items, task)
        except Exception as exc:
            return jsonify({"error": type(exc).__name__, "detail": str(exc)}), 500
        return jsonify(
            {
                "embedding": vectors[0],
                "embeddings": vectors,
                "vector": vectors[0],
                "model": "wemm-embedding-2b",
                "dim": EMBEDDING_DIM,
                "device": "cpu",
            }
        )

    @app.route("/health", methods=["GET"])
    def health():
        import torch

        ready = _model is not None
        payload = {
            "status": "ok" if ready else "loading",
            "model": "wemm-embedding-2b",
            "dim": EMBEDDING_DIM,
            "device": "cpu",
            "cuda_visible": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "torch_cuda": torch.cuda.is_available(),
            "bind": "127.0.0.1",
            "ready": ready,
        }
        return jsonify(payload), (200 if ready else 503)

    return app


def main() -> int:
    port = int(os.environ.get("EMBEDDING_SERVICE_PORT", "18890"))
    host = os.environ.get("EMBEDDING_BIND_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost"}:
        print("refusing non-loopback bind", file=sys.stderr)
        return 2
    _get_model()
    app = create_app()
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
