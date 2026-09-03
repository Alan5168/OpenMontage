"""RunningHub Workflow API adapter — cloud factory, not a second OM.

Official flow: upload → /task/openapi/create → taskId → /task/openapi/outputs.
https://www.runninghub.ai/runninghub-api-doc-en/api-425761093

Quote before spend. Submit requires confirm + API key + workflow_id.
Does not call dispatch_cut. SUCCESS ≠ OM PASS.
Consumer membership ≠ Model API. Workflow API may still bill coins.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import requests
import yaml

from lib.shot_render_package import sha256_file, sha256_json

DEFAULT_HOST = "www.runninghub.ai"
PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles" / "runninghub"
AUTH_PROFILE = "runninghub_default"
DEFAULT_API_JSON = Path(
    r"C:\ContentStudio\jobs\rh-001-provider-lifecycle-v1\working\API_WORKFLOW.json"
)
_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "apiKey",
        "RUNNINGHUB_API_KEY",
        "authorization",
        "Authorization",
        "token",
        "secret",
    }
)

# From the official integration example (poll /task/openapi/outputs).
RH_RUNNING = 804
RH_QUEUED = 813
RH_FAILED = 805


class RunningHubError(RuntimeError):
    """RunningHub adapter refused or the API returned a failure."""


def api_host() -> str:
    return (os.environ.get("RUNNINGHUB_API_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST


def api_key() -> str | None:
    key = (os.environ.get("RUNNINGHUB_API_KEY") or "").strip()
    return key or None


def load_profile(profile_id: str = "rh_h3_fl2va_final_v1") -> dict[str, Any]:
    path = PROFILE_DIR / f"{profile_id}.yaml"
    if not path.is_file():
        raise RunningHubError(f"missing RunningHub profile: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RunningHubError(f"invalid profile YAML: {path}")
    for banned in ("api_key", "apikey", "RUNNINGHUB_API_KEY", "secret"):
        if payload.get(banned):
            raise RunningHubError(
                "api_key must not live in YAML; set RUNNINGHUB_API_KEY in the environment"
            )
    env_wf = (os.environ.get("RUNNINGHUB_WORKFLOW_ID") or "").strip()
    if env_wf:
        payload["workflow_id"] = env_wf
    return payload


def quote_runninghub(package: dict[str, Any], *, profile_id: str = "rh_h3_fl2va_final_v1") -> dict[str, Any]:
    profile = load_profile(profile_id)
    workflow_id = str(profile.get("workflow_id") or "").strip()
    return {
        "quoted": True,
        "tool": "runninghub_workflow",
        "provider": "runninghub",
        "profile": profile_id,
        "workflow_id_present": bool(workflow_id),
        "workflow_api_json_sha256_present": bool(
            str(profile.get("workflow_api_json_sha256") or "").strip()
        ),
        "api_key_present": api_key() is not None,
        "usd": None,
        "coins": None,
        "coins_unknown": True,
        "requires_confirm": True,
        "execute": False,
        "membership_note": (
            "Workflow API can use Consumer-Member or Enterprise-Shared keys. "
            "Model API / LLM need Enterprise-Shared. Website sub is not all APIs. "
            "Run a bill smoke on your own key before hero spend."
        ),
        "package_sha256": package.get("package_sha256"),
        "not_retryable": ["insufficient_credits", "402", "moderation", "copyright", "quota"],
    }


def compile_runninghub(
    package: dict[str, Any],
    *,
    profile_id: str | None = None,
) -> dict[str, Any]:
    policy = package.get("render_policy") or {}
    profile_id = profile_id or str(policy.get("profile") or "rh_h3_fl2va_final_v1")
    profile = load_profile(profile_id)
    first = (package.get("frames") or {}).get("first_frame") or {}
    return {
        "target": "runninghub",
        "provider": "runninghub",
        "mode": "workflow_api",
        "profile": profile_id,
        "workflow_id": str(profile.get("workflow_id") or ""),
        "workflow_api_json_sha256": str(profile.get("workflow_api_json_sha256") or "") or None,
        "first_frame_sha256": first.get("sha256"),
        "first_frame_kind": first.get("kind"),
        "node_info_list": [],
        "submit": False,
        "needs_upload": bool(first.get("asset_ref")),
        "blockers": lifecycle_blockers(profile),
    }


def profile_bindings(profile: dict[str, Any]) -> dict[str, Any]:
    if isinstance(profile.get("bindings"), dict):
        return profile["bindings"]
    if isinstance(profile.get("input_map"), dict):
        return profile["input_map"]
    return {}


def slot_binding(profile: dict[str, Any], name: str) -> tuple[str, str]:
    spec = profile_bindings(profile).get(name)
    spec = spec if isinstance(spec, dict) else {}
    node_id = str(spec.get("node_id") or spec.get("nodeId") or "").strip()
    field = str(spec.get("field") or spec.get("fieldName") or "").strip()
    return node_id, field


def workflow_api_json_path(profile: dict[str, Any]) -> Path:
    raw = str(profile.get("workflow_api_json") or "").strip()
    return Path(raw) if raw else DEFAULT_API_JSON


def lifecycle_blockers(profile: dict[str, Any] | None = None) -> list[str]:
    """RH-001 cannot submit until clone + API export + hash + key exist."""
    profile = profile if isinstance(profile, dict) else load_profile()
    first_id, _ = slot_binding(profile, "first_frame")
    prompt_id, _ = slot_binding(profile, "prompt")
    expected = str(profile.get("workflow_api_json_sha256") or "").strip().lower()
    api_json = workflow_api_json_path(profile)
    blockers: list[str] = []
    if not str(profile.get("workflow_id") or "").strip():
        blockers.append("workflow_id_missing")
    if not first_id:
        blockers.append("first_frame_nodeId_missing")
    if not prompt_id:
        blockers.append("prompt_nodeId_missing")
    if not expected:
        blockers.append("workflow_api_json_sha256_missing")
    elif not api_json.is_file():
        blockers.append("workflow_api_json_missing")
    elif sha256_file(api_json) != expected:
        blockers.append("workflow_api_json_hash_mismatch")
    if api_key() is None:
        blockers.append("RUNNINGHUB_API_KEY_missing")
    return blockers


def file_name_from_upload(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    name = str(data.get("fileName") or data.get("file_name") or "").strip()
    if not name:
        raise RunningHubError(f"upload returned no fileName: {payload}")
    return name


def external_handle(
    *,
    external_asset_id: str,
    source_sha256: str | None,
    kind: str = "first_frame",
    provider: str = "runninghub",
) -> dict[str, str | None]:
    """Provider-side cache pointer. Not an OM asset registry row."""
    return {
        "provider": provider,
        "external_asset_id": external_asset_id,
        "source_sha256": source_sha256,
        "kind": kind,
    }


def build_node_info_list(
    package: dict[str, Any],
    *,
    profile: dict[str, Any] | None = None,
    first_frame_file_name: str | None = None,
    last_frame_file_name: str | None = None,
) -> list[dict[str, str]]:
    profile = profile if isinstance(profile, dict) else load_profile(
        str((package.get("render_policy") or {}).get("profile") or "rh_h3_fl2va_final_v1")
    )
    prompt = str((package.get("provider_prompt") or {}).get("neutral_prompt") or "")
    rows: list[dict[str, str]] = []

    def _add(map_key: str, value: str | None, default_field: str) -> None:
        node_id, field = slot_binding(profile, map_key)
        if not node_id or not value:
            return
        rows.append(
            {
                "nodeId": node_id,
                "fieldName": field or default_field,
                "fieldValue": value,
            }
        )

    _add("prompt", prompt, "text")
    _add("first_frame", first_frame_file_name, "image")
    _add("last_frame", last_frame_file_name, "image")
    duration = (package.get("creative") or {}).get("duration_s")
    if duration is not None:
        _add("duration", str(duration), "value")
    return rows


def select_output_url(payload: dict[str, Any]) -> str | None:
    data = payload.get("data")
    rows = data if isinstance(data, list) else []
    if isinstance(data, dict):
        nested = data.get("outputs") or data.get("files") or []
        rows = nested if isinstance(nested, list) else [data]
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(row.get("fileUrl") or row.get("url") or row.get("file_url") or "").strip()
        if not url:
            continue
        kind = str(row.get("fileType") or row.get("type") or url).lower()
        if "mp4" in kind or "video" in kind or url.lower().endswith(".mp4"):
            return url
    for row in rows:
        if isinstance(row, dict):
            url = str(row.get("fileUrl") or row.get("url") or "").strip()
            if url:
                return url
    return None


def poll_outputs(
    *,
    task_id: str,
    key: str | None = None,
    timeout_s: float = 900,
    interval_s: float = 5,
    sleeper: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    sleep = sleeper or time.sleep
    deadline = time.monotonic() + float(timeout_s)
    last: dict[str, Any] = {}
    while time.monotonic() <= deadline:
        last = query_outputs(task_id=task_id, key=key)
        if outputs_failed(last):
            raise RunningHubError(f"task failed: {last}")
        if outputs_ready(last) and select_output_url(last):
            return last
        sleep(float(interval_s))
    raise RunningHubError(f"poll timeout after {timeout_s}s: {last}")


def run_lifecycle(
    package: dict[str, Any],
    *,
    dest_dir: Path,
    confirm: bool,
    submit: bool,
    profile_id: str = "rh_h3_fl2va_final_v1",
    sleeper: Callable[[float], None] | None = None,
    upload: Callable[..., dict[str, Any]] | None = None,
    create: Callable[..., dict[str, Any]] | None = None,
    poll: Callable[..., dict[str, Any]] | None = None,
    download: Callable[..., Path] | None = None,
) -> dict[str, Any]:
    """RH-001 path. Quote is always legal. Submit needs confirm + empty blockers.

    OUTPUT_RECEIVED is not QUALITY_PASS. Uses existing Observation, not a
    RunningHub observer.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    profile = load_profile(profile_id)
    blockers = lifecycle_blockers(profile)
    quote = quote_runninghub(package, profile_id=profile_id)
    handles: list[dict[str, str | None]] = []
    workflow_id = str(profile.get("workflow_id") or "") or None
    workflow_json_hash = str(profile.get("workflow_api_json_sha256") or "") or None
    receipt_kwargs = {
        "dest": dest_dir / "RECEIPT.json",
        "package": package,
        "profile_id": profile_id,
        "provider_handles": handles,
        "workflow_id": workflow_id,
        "workflow_json_hash": workflow_json_hash,
    }
    if not submit:
        receipt = write_receipt(
            **receipt_kwargs,
            status="QUOTED_AWAITING_SUBMIT",
        )
        observation = write_observation(
            dest_dir / "OBSERVATION.json",
            status="PACKAGE_READY",
            receipt_path=dest_dir / "RECEIPT.json",
            note="RH-001 quote only. Not OUTPUT_RECEIVED. Not QUALITY_PASS.",
        )
        return {
            "ok": True,
            "submit": False,
            "blockers": blockers,
            "quote": quote,
            "receipt": receipt,
            "observation": observation,
        }
    if not confirm:
        raise RunningHubError("submit refused: quote requires_confirm; pass confirm=true")
    if blockers:
        raise RunningHubError("submit blocked: " + ",".join(blockers))

    started = time.monotonic()
    first = (package.get("frames") or {}).get("first_frame") or {}
    first_path = Path(str(first.get("asset_ref") or ""))
    uploader = upload or upload_file
    uploaded = uploader(first_path)
    file_name = file_name_from_upload(uploaded)
    handles.append(
        external_handle(
            external_asset_id=file_name,
            source_sha256=str(first.get("sha256") or ""),
            kind="first_frame",
        )
    )
    node_info = build_node_info_list(package, profile=profile, first_frame_file_name=file_name)
    creator = create or submit_task
    created = creator(
        workflow_id=str(profile.get("workflow_id") or ""),
        node_info_list=node_info,
        confirm=True,
    )
    data = created.get("data") if isinstance(created.get("data"), dict) else {}
    task_id = str(data.get("taskId") or "")
    if not task_id:
        raise RunningHubError(f"create returned no taskId: {created}")
    poller = poll or (lambda **kwargs: poll_outputs(sleeper=sleeper, **kwargs))
    outputs = poller(task_id=task_id)
    url = select_output_url(outputs)
    if not url:
        raise RunningHubError(f"no output url: {outputs}")
    out_path = dest_dir / "output.mp4"
    downloader = download or receive_file
    downloader(url, out_path)
    wall_time_s = round(time.monotonic() - started, 3)
    usage = extract_usage(created, outputs, uploaded, wall_time_s=wall_time_s)
    receipt = write_receipt(
        **receipt_kwargs,
        status="OUTPUT_RECEIVED",
        provider_job_id=task_id,
        output_path=out_path,
        usage=usage,
    )
    observation = write_observation(
        dest_dir / "OBSERVATION.json",
        status="OUTPUT_RECEIVED",
        receipt_path=dest_dir / "RECEIPT.json",
        note=(
            "Cloud file in is OUTPUT_RECEIVED, not OM PASS, not QUALITY_PASS, "
            "not FIRST_TAKE_ACCEPTABLE. Same Observation / REVIEW_QUEUE as local H3."
        ),
    )
    return {
        "ok": True,
        "submit": True,
        "task_id": task_id,
        "blockers": [],
        "quote": quote,
        "receipt": receipt,
        "observation": observation,
        "provider_handles": handles,
        "output_path": str(out_path).replace("\\", "/"),
    }


def _headers(key: str) -> dict[str, str]:
    return {
        "Host": api_host(),
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def upload_file(path: Path, *, key: str | None = None) -> dict[str, Any]:
    token = key or api_key()
    if not token:
        raise RunningHubError("RUNNINGHUB_API_KEY missing")
    if not path.is_file():
        raise RunningHubError(f"upload missing: {path}")
    url = f"https://{api_host()}/task/openapi/upload"
    with path.open("rb") as handle:
        resp = requests.post(
            url,
            headers={"Host": api_host(), "Authorization": f"Bearer {token}"},
            data={"apiKey": token, "fileType": "input"},
            files={"file": (path.name, handle)},
            timeout=120,
        )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") not in (0, None) and payload.get("msg") not in {"success", None}:
        if payload.get("code") not in (0, "0"):
            raise RunningHubError(f"upload refused: {payload}")
    return payload


def submit_task(
    *,
    workflow_id: str,
    node_info_list: list[dict[str, Any]],
    confirm: bool,
    key: str | None = None,
) -> dict[str, Any]:
    if not confirm:
        raise RunningHubError("submit refused: quote requires_confirm; pass confirm=true")
    token = key or api_key()
    if not token:
        raise RunningHubError("RUNNINGHUB_API_KEY missing")
    workflow_id = str(workflow_id or "").strip()
    if not workflow_id:
        raise RunningHubError("workflow_id missing — set profile or RUNNINGHUB_WORKFLOW_ID")
    url = f"https://{api_host()}/task/openapi/create"
    body = {
        "apiKey": token,
        "workflowId": workflow_id,
        "nodeInfoList": node_info_list,
        "addMetadata": True,
    }
    resp = requests.post(url, headers=_headers(token), json=body, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") not in (0, "0"):
        raise RunningHubError(f"create refused: {payload}")
    data = payload.get("data") or {}
    task_id = data.get("taskId")
    if task_id is None:
        raise RunningHubError(f"create returned no taskId: {payload}")
    return payload


def query_outputs(*, task_id: str, key: str | None = None) -> dict[str, Any]:
    token = key or api_key()
    if not token:
        raise RunningHubError("RUNNINGHUB_API_KEY missing")
    url = f"https://{api_host()}/task/openapi/outputs"
    resp = requests.post(
        url,
        headers=_headers(token),
        json={"apiKey": token, "taskId": str(task_id)},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def outputs_ready(payload: dict[str, Any]) -> bool:
    code = payload.get("code")
    data = payload.get("data")
    return code in (0, "0") and bool(data)


def outputs_failed(payload: dict[str, Any]) -> bool:
    return payload.get("code") == RH_FAILED


def extract_usage(*payloads: dict[str, Any], wall_time_s: float | None = None) -> dict[str, Any]:
    """Never guess. Null unless a payload actually reports a number."""
    coins = None
    usd = None
    keys_coins = ("rh_coins", "consumeCoins", "consumeCredit", "coins", "credit")
    keys_usd = ("usd", "wallet_usd", "amountUsd")
    for payload in payloads:
        data = payload.get("data") if isinstance(payload, dict) else None
        blobs = [payload]
        if isinstance(data, dict):
            blobs.append(data)
        for blob in blobs:
            if not isinstance(blob, dict):
                continue
            for key in keys_coins:
                if coins is None and isinstance(blob.get(key), (int, float)):
                    coins = blob[key]
            for key in keys_usd:
                if usd is None and isinstance(blob.get(key), (int, float)):
                    usd = blob[key]
    return {"rh_coins": coins, "wallet_usd": usd, "wall_time_s": wall_time_s}


def probe_output(path: Path) -> dict[str, Any]:
    """File hash always. Geometry/duration only if ffprobe reports them."""
    row: dict[str, Any] = {
        "path": str(path).replace("\\", "/"),
        "sha256": sha256_file(path) if path.is_file() else None,
        "duration_s": None,
        "width": None,
        "height": None,
    }
    if not path.is_file():
        return row
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            payload = json.loads(proc.stdout)
            stream = (payload.get("streams") or [{}])[0]
            if stream.get("width"):
                row["width"] = int(stream["width"])
            if stream.get("height"):
                row["height"] = int(stream["height"])
            if stream.get("duration"):
                row["duration_s"] = float(stream["duration"])
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return row


def _receipt_has_secret(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in _SECRET_KEYS:
                return True
            if _receipt_has_secret(value):
                return True
        return False
    if isinstance(payload, list):
        return any(_receipt_has_secret(item) for item in payload)
    text = str(payload)
    live = api_key()
    return bool(live) and live in text


def receive_file(file_url: str, dest: Path, timeout: int = 300) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(file_url, timeout=timeout)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def write_receipt(
    *,
    dest: Path,
    package: dict[str, Any],
    profile_id: str,
    status: str,
    provider_job_id: str | None = None,
    output_path: Path | None = None,
    cost: dict[str, Any] | None = None,
    error: str | None = None,
    provider_handles: list[dict[str, Any]] | None = None,
    workflow_id: str | None = None,
    workflow_json_hash: str | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    first = (package.get("frames") or {}).get("first_frame") or {}
    prompt = str((package.get("provider_prompt") or {}).get("neutral_prompt") or "")
    usage_row = usage or {"rh_coins": None, "wallet_usd": None, "wall_time_s": None}
    receipt = {
        "schema_version": "om-external-provider-receipt/v1",
        "shot_id": package.get("shot_id"),
        "provider": "runninghub",
        "provider_mode": "workflow_api",
        "profile": profile_id,
        "auth_profile": AUTH_PROFILE,
        "workflow_id": workflow_id,
        "provider_task_id": provider_job_id,
        "provider_job_id": provider_job_id,
        "inputs": {
            "package_hash": package.get("package_sha256"),
            "workflow_json_hash": workflow_json_hash,
            "first_frame_hash": first.get("sha256"),
            "first_frame_kind": first.get("kind"),
            "prompt_hash": sha256_json({"prompt": prompt}) if prompt else None,
            "provider_handles": provider_handles or [],
        },
        "output": None,
        "usage": {
            "rh_coins": usage_row.get("rh_coins"),
            "wallet_usd": usage_row.get("wallet_usd"),
            "wall_time_s": usage_row.get("wall_time_s"),
        },
        "cost": cost
        or {
            "credits": usage_row.get("rh_coins"),
            "usd": usage_row.get("wallet_usd"),
            "coins": usage_row.get("rh_coins"),
        },
        "status": status,
        "human_approved": False,
        "om_pass": False,
        "error": error,
        "note": (
            "OUTPUT_RECEIVED is not OM PASS and not QUALITY_PASS. "
            "Observation + human review still required. "
            "If the API omitted cost, leave usage null and fill from the UI later."
        ),
    }
    if output_path is not None and output_path.is_file():
        receipt["output"] = probe_output(output_path)
    if _receipt_has_secret(receipt):
        raise RunningHubError("receipt refused: secret must not be persisted")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def write_observation(
    dest: Path,
    *,
    status: str,
    receipt_path: Path | None,
    note: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": "om-external-provider-observation/v1",
        "status": status,
        "first_take_acceptable": False,
        "content_fail": False,
        "receipt": str(receipt_path).replace("\\", "/") if receipt_path else None,
        "note": note,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def write_review_queue(dest: Path, *, shot_id: str, receipt_status: str) -> dict[str, Any]:
    payload = {
        "schema_version": "om-review-queue/v1",
        "shot_id": shot_id,
        "provider": "runninghub",
        "receipt_status": receipt_status,
        "human_approved": False,
        "ab": None,
        "decision": None,
        "choices": ["CONTINUE", "REVISE", "SHIP"],
        "ab_choices": ["A", "B", "NEITHER"],
        "note": "Cloud file in is not SHIP. Alan picks A/B/NEITHER then CONTINUE/REVISE/SHIP.",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
