#!/usr/bin/env python3
r"""Migrate nf_stock_footage_v1 -> nf_stock_footage_v2 with doubao-embedding-vision multimodal vectors.

Text+image (f0 thumb) per point, 1024 dims, v1 untouched. Resumable via checkpoint.
Spec: C:\ContentStudio\jobs\qdrant-v2-multimodal-migration-20260903\task_spec.md
"""
from __future__ import annotations

import base64
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

QDRANT = "http://127.0.0.1:6333"
V1 = "nf_stock_footage_v1"
V2 = "nf_stock_footage_v2"
THUMB_ROOT = Path(r"C:\ContentStudio\media\stock-metadata")
ARK_MM = "https://ark.cn-beijing.volces.com/api/coding/v3/embeddings/multimodal"
MODEL = "doubao-embedding-vision"
DIMS = 1024
CHECKPOINT = Path(r"C:\ContentStudio\logs\migrate_qdrant_v2_checkpoint.json")
LOG = Path(r"C:\ContentStudio\logs\migrate_qdrant_v2_20260903.log")
BATCH = 64
WORKERS = 6
MAX_RETRY = 5
ABORT_AFTER_FAILS = 20


def get_key() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _ = winreg.QueryValueEx(k, "OPENVIKING_ARK_EMBEDDING_API_KEY")
            if v:
                return v
    except OSError:
        pass
    v = os.environ.get("OPENVIKING_ARK_EMBEDDING_API_KEY")
    if not v:
        raise SystemExit("FATAL: no API key in HKCU or env")
    return v


KEY = get_key()


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http_json(method: str, url: str, body: dict | None, timeout: int = 60):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if "volces.com" in url:
        headers["Authorization"] = "Bearer " + KEY
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def build_text(p: dict) -> str:
    parts = []
    if p.get("category"):
        parts.append(p["category"])
    if p.get("subcategory"):
        parts.append(p["subcategory"])
    for label, field in (("场景", "scene"), ("主体", "subject"), ("动作", "action"),
                         ("情绪", "mood"), ("风格", "style")):
        if p.get(field):
            parts.append(f"{label}：{p[field]}")
    if p.get("tags"):
        parts.append("标签：" + "、".join(p["tags"]))
    if p.get("reuse_hint"):
        parts.append("用途：" + p["reuse_hint"])
    return "。".join(parts)


def load_thumb_b64(p: dict) -> str | None:
    tp = p.get("thumb_paths")
    if not tp:
        return None
    path = THUMB_ROOT / tp[0]
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) < 1024:
        return None
    return base64.b64encode(raw).decode()


def embed_point(p: dict) -> list[float]:
    text = build_text(p)
    b64 = load_thumb_b64(p)
    content = [{"type": "text", "text": text}] if text else []
    if b64:
        content.append({"type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64," + b64}})
    if not content:
        raise ValueError(f"point {p.get('content_id')} has no text and no thumb")
    body = {"model": MODEL, "dimensions": DIMS, "input": content}
    last_err = None
    for attempt in range(MAX_RETRY):
        try:
            resp = http_json("POST", ARK_MM, body)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        data = resp.get("data")
        if isinstance(data, dict):
            emb = data.get("embedding")
        elif isinstance(data, list) and data:
            emb = data[0].get("embedding")
        else:
            emb = None
        if not isinstance(emb, list) or len(emb) != DIMS:
            raise ValueError(f"bad embedding payload for {p.get('content_id')}")
        return emb
    raise last_err


def scroll_v1() -> list[dict]:
    points, offset = [], None
    while True:
        body = {"limit": 256, "with_payload": True}
        if offset is not None:
            body["offset"] = offset
        resp = http_json("POST", f"{QDRANT}/collections/{V1}/points/scroll", body, timeout=30)
        res = resp.get("result", {})
        points.extend(res.get("points", []))
        offset = res.get("next_page_offset")
        if offset is None:
            break
    return points


def load_checkpoint() -> dict:
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    return {"done_ids": [], "failed": 0, "text_only": 0, "errors": []}


def save_checkpoint(cp: dict) -> None:
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(cp, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CHECKPOINT)


def upsert_batch(batch: list[dict]) -> None:
    body = {"points": batch}
    http_json("PUT", f"{QDRANT}/collections/{V2}/points?wait=true", body, timeout=120)


def main() -> int:
    # ensure v2 exists (idempotent)
    try:
        http_json("GET", f"{QDRANT}/collections/{V2}", None, timeout=10)
        log(f"collection {V2} already exists")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            http_json("PUT", f"{QDRANT}/collections/{V2}",
                      {"vectors": {"size": DIMS, "distance": "Cosine"}}, timeout=30)
            log(f"collection {V2} created ({DIMS}d Cosine)")
        else:
            raise

    all_pts = scroll_v1()
    log(f"v1 scrolled: {len(all_pts)} points")
    cp = load_checkpoint()
    done = set(cp["done_ids"])
    todo = [pt for pt in all_pts if pt["id"] not in done]
    log(f"already done: {len(done)}, todo: {len(todo)}")
    if not todo:
        log("nothing to do, finished")
        return 0

    t0 = time.time()
    processed = 0
    fails_in_row = 0
    batch: list[dict] = []

    def flush():
        nonlocal batch
        if batch:
            upsert_batch(batch)
            save_checkpoint(cp)
            batch = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {}
        pending = list(todo)
        idx = 0
        while idx < len(pending) or futures:
            while idx < len(pending) and len(futures) < WORKERS:
                pt = pending[idx]
                futures[ex.submit(embed_point, pt["payload"])] = pt
                idx += 1
            done_f, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED)
            for fut in done_f:
                pt = futures.pop(fut)
                try:
                    vec = fut.result()
                    if load_thumb_b64(pt["payload"]) is None:
                        cp["text_only"] += 1
                    payload = dict(pt["payload"])
                    payload["embedding_model"] = "doubao-embedding-vision-1024"
                    batch.append({"id": pt["id"], "vector": vec, "payload": payload})
                    cp["done_ids"].append(pt["id"])
                    processed += 1
                    fails_in_row = 0
                    if len(batch) >= BATCH:
                        flush()
                    if processed % 500 == 0:
                        rate = processed / max(time.time() - t0, 0.1)
                        eta = (len(pending) - idx - len(futures)) / rate / 60
                        log(f"progress {processed}/{len(pending)} "
                            f"rate={rate:.1f}/s eta={eta:.1f}min")
                except Exception as e:
                    cp["failed"] += 1
                    cp["errors"].append({"id": pt["id"], "err": str(e)[:200]})
                    fails_in_row += 1
                    log(f"ERROR point {pt['id']}: {e}")
                    if fails_in_row >= ABORT_AFTER_FAILS:
                        log(f"ABORT: {ABORT_AFTER_FAILS} consecutive failures")
                        flush()
                        save_checkpoint(cp)
                        return 1
                if len(cp["errors"]) > 500:
                    cp["errors"] = cp["errors"][-100:]
    flush()
    save_checkpoint(cp)
    dt = time.time() - t0
    log(f"DONE: {processed} ok, {cp['failed']} failed, {cp['text_only']} text-only, "
        f"{dt/60:.1f} min, checkpoint saved")
    return 0 if cp["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
