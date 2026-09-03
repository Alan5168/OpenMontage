"""Layout geometry check — exception diagnostic, not the shot pipeline.

Not a critic that APPROVES. Not a new Agent. Prime owns intent.
Do not run this before every shot. Use it when SEE or a still is
spatially absurd (person on a table, height that cannot exist at
that footpoint). Normal path is storyboard → one layout/keyframe
per shot → LIMITED or H3 → SEE.

This function only answers whether a footpoint and a pixel height
can coexist on a ground plane. Language models do not own camera /
depth / bbox. If MoGe-2 or GeoCalib cannot be imported, classical
vanishing-point + similar triangles still run.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ACTOR_HEIGHT_M = 1.75
CAMERA_HEIGHT_M = 1.55
ACTOR_HEIGHT_RANGE_M = (1.65, 1.85)
CAMERA_HEIGHT_RANGE_M = (1.45, 1.70)


@dataclass(frozen=True)
class Footpoint:
    name: str
    xy_frac: tuple[float, float]
    zone: str


def _cv2():
    import cv2  # type: ignore

    return cv2


def _load_rgb(path: Path) -> np.ndarray:
    cv2 = _cv2()
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def detect_vanishing_point(rgb: np.ndarray) -> dict[str, Any]:
    """RANSAC intersection of long non-horizontal lines. Kitchen 1-point EST."""
    cv2 = _cv2()
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 60, 160)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=max(60, min(w, h) // 24),
        minLineLength=min(w, h) // 8, maxLineGap=20,
    )
    segs: list[tuple[float, float, float, float]] = []
    if lines is not None:
        pts = np.asarray(lines).reshape(-1, 4)
        for x1, y1, x2, y2 in pts:
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 40:
                continue
            ang = abs(math.degrees(math.atan2(dy, dx)))
            if ang < 8 or ang > 172:
                continue
            segs.append((x1, y1, x2, y2))
    if len(segs) < 4:
        return {
            "ok": False,
            "vanishing_point_px": [w / 2, h / 2],
            "horizon_y": h / 2,
            "line_count": len(segs),
            "method": "fallback_frame_center",
        }

    rng = np.random.default_rng(0)
    best = None
    best_count = -1
    for _ in range(250):
        i, j = rng.choice(len(segs), size=2, replace=False)
        p = _intersect(segs[i], segs[j])
        if p is None:
            continue
        px, py = p
        if not (-0.5 * w < px < 1.5 * w and -0.5 * h < py < 1.5 * h):
            continue
        count = sum(1 for seg in segs if _dist_point_line(px, py, seg) < 8)
        if count > best_count:
            best_count = count
            best = (px, py)
    if best is None:
        best = (w / 2, h / 2)
        best_count = 0
    return {
        "ok": best_count >= 4,
        "vanishing_point_px": [float(best[0]), float(best[1])],
        "horizon_y": float(best[1]),
        "line_count": len(segs),
        "inliers": int(best_count),
        "method": "hough_ransac_vp",
    }


def _intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float] | None:
    x1, y1, x2, y2 = a
    x3, y3, x4, y4 = b
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-6:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
    return float(px), float(py)


def _dist_point_line(
    px: float, py: float, seg: tuple[float, float, float, float]
) -> float:
    x1, y1, x2, y2 = seg
    dx, dy = x2 - x1, y2 - y1
    mag = math.hypot(dx, dy) or 1.0
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / mag


def similar_triangles_height_px(
    foot_y: float,
    horizon_y: float,
    actor_m: float = ACTOR_HEIGHT_M,
    camera_m: float = CAMERA_HEIGHT_M,
) -> float | None:
    """Level-camera ground plane: height_px = (H_actor / H_cam) * (foot_y - horizon_y)."""
    dy = float(foot_y) - float(horizon_y)
    if dy <= 4:
        return None
    return float((actor_m / camera_m) * dy)


def height_range_px(foot_y: float, horizon_y: float) -> tuple[float, float] | None:
    dy = float(foot_y) - float(horizon_y)
    if dy <= 4:
        return None
    lo = (ACTOR_HEIGHT_RANGE_M[0] / CAMERA_HEIGHT_RANGE_M[1]) * dy
    hi = (ACTOR_HEIGHT_RANGE_M[1] / CAMERA_HEIGHT_RANGE_M[0]) * dy
    return (float(lo), float(hi))


def project_actor_bbox(
    foot_xy: tuple[float, float],
    height_px: float,
    frame_wh: tuple[int, int],
    aspect: float = 0.32,
) -> list[int]:
    fx, fy = foot_xy
    w, h = frame_wh
    box_h = max(8.0, height_px)
    box_w = box_h * aspect
    x0 = int(round(fx - box_w / 2))
    y0 = int(round(fy - box_h))
    x1 = int(round(fx + box_w / 2))
    y1 = int(round(fy))
    return [x0, y0, x1, y1]


def _try_geocalib(rgb: np.ndarray, device: str) -> dict[str, Any] | None:
    try:
        import torch
        from geocalib import GeoCalib
    except Exception as exc:
        return {"ok": False, "error": f"geocalib_import: {exc}"}
    try:
        model = GeoCalib().to(device)
        tensor = torch.tensor(rgb / 255.0, dtype=torch.float32, device=device).permute(2, 0, 1)
        with torch.inference_mode():
            result = model.calibrate(tensor)
        cam = result["camera"]
        grav = result["gravity"]
        out: dict[str, Any] = {"ok": True, "backend": "geocalib"}
        for key in ("size", "f", "vfov", "focal"):
            if hasattr(cam, key):
                val = getattr(cam, key)
                out[key] = _to_jsonable(val)
        if hasattr(cam, "f"):
            f = cam.f
            out["focal_px"] = _to_jsonable(f)
        if hasattr(grav, "vec3d"):
            out["gravity"] = _to_jsonable(grav.vec3d)
        elif hasattr(grav, "gravity"):
            out["gravity"] = _to_jsonable(grav.gravity)
        else:
            out["gravity"] = _to_jsonable(grav)
        # Horizon: where gravity-projected rays at image x=center hit infinite plane.
        h, w = rgb.shape[:2]
        if hasattr(grav, "roll") and hasattr(grav, "pitch"):
            out["roll"] = _to_jsonable(grav.roll)
            out["pitch"] = _to_jsonable(grav.pitch)
        horizon_y = _horizon_from_geocalib(cam, grav, w, h)
        if horizon_y is not None:
            out["horizon_y"] = float(horizon_y)
        return out
    except Exception as exc:
        return {"ok": False, "error": f"geocalib_infer: {exc}"}


def _horizon_from_geocalib(cam: Any, grav: Any, w: int, h: int) -> float | None:
    try:
        import torch

        g = grav.vec3d if hasattr(grav, "vec3d") else None
        if g is None:
            return None
        g = g.detach().float().cpu().view(-1)
        # OpenCV: gravity down in camera frame. Horizon is perpendicular to gravity
        # through the principal point in the image, for small roll:
        # v = cy - fy * gx/gy  is wrong; for pinhole, horizon line n·K^{-1}p = 0
        # with n = gravity. Simplified level-ish: horizon_y ≈ cy + fy * (gx? pitch)
        fy = None
        cy = h / 2
        if hasattr(cam, "f"):
            f = cam.f.detach().float().cpu().view(-1)
            fy = float(f[1] if f.numel() > 1 else f[0])
        if hasattr(cam, "c"):
            c = cam.c.detach().float().cpu().view(-1)
            cy = float(c[1] if c.numel() > 1 else h / 2)
        if fy is None:
            return None
        gx, gy, gz = (float(g[0]), float(g[1]), float(g[2]))
        # Ray through (u, v, 1) is perpendicular to gravity on the horizon:
        # g · K^{-1}[u,v,1] = 0. At u = cx ≈ w/2:
        # gx*(u-cx)/fx + gy*(v-cy)/fy + gz = 0
        fx = fy
        cx = w / 2
        if hasattr(cam, "c"):
            c = cam.c.detach().float().cpu().view(-1)
            cx = float(c[0])
        if abs(gy) < 1e-5:
            return None
        v = cy - fy * (gx * (cx - cx) / fx + gz) / gy
        # gx term is 0 at u=cx. v = cy - fy * gz / gy
        v = cy - fy * (gz / gy)
        return float(v)
    except Exception:
        return None


def _try_moge(rgb: np.ndarray, device: str) -> dict[str, Any] | None:
    try:
        import torch
        from moge.model.v2 import MoGeModel
    except Exception as exc:
        return {"ok": False, "error": f"moge_import: {exc}"}
    try:
        model = MoGeModel.from_pretrained("Ruicheng/moge-2-vits-normal").to(device).eval()
        tensor = torch.tensor(rgb / 255.0, dtype=torch.float32, device=device).permute(2, 0, 1)
        with torch.inference_mode():
            output = model.infer(tensor, use_fp16=True)
        points = output["points"].detach().float().cpu().numpy()
        depth = output["depth"].detach().float().cpu().numpy()
        mask = output["mask"].detach().float().cpu().numpy() > 0.5
        K = output["intrinsics"].detach().float().cpu().numpy()
        normal = None
        if "normal" in output and output["normal"] is not None:
            normal = output["normal"].detach().float().cpu().numpy()
        fov = None
        try:
            import utils3d

            fx = float(K[0, 0])
            fy = float(K[1, 1])
            # utils3d expects normalized or pixel; record both interpretations
            fov = {"fx": fx, "fy": fy, "cx": float(K[0, 2]), "cy": float(K[1, 2])}
        except Exception:
            fov = {"K": K.tolist()}
        return {
            "ok": True,
            "backend": "moge-2-vits-normal",
            "points": points,
            "depth": depth,
            "mask": mask,
            "normal": normal,
            "intrinsics": K,
            "fov": fov,
        }
    except Exception as exc:
        return {"ok": False, "error": f"moge_infer: {exc}"}


def _to_jsonable(val: Any) -> Any:
    try:
        import torch

        if isinstance(val, torch.Tensor):
            return val.detach().float().cpu().reshape(-1).tolist()
    except Exception:
        pass
    if isinstance(val, np.ndarray):
        return val.tolist()
    if hasattr(val, "tolist"):
        try:
            return val.tolist()
        except Exception:
            pass
    if isinstance(val, (float, int, str, bool)) or val is None:
        return val
    return str(val)[:200]


def moge_actor_at_foot(
    moge: dict[str, Any],
    foot_xy: tuple[float, float],
    actor_m: float,
    gravity: np.ndarray | None,
) -> dict[str, Any] | None:
    points = moge.get("points")
    mask = moge.get("mask")
    K = moge.get("intrinsics")
    if points is None or K is None:
        return None
    h, w = points.shape[:2]
    u = int(round(foot_xy[0]))
    v = int(round(foot_xy[1]))
    u = min(max(u, 0), w - 1)
    v = min(max(v, 0), h - 1)
    if mask is not None and not bool(mask[v, u]):
        return {"ok": False, "reason": "foot_pixel_invalid_in_moge_mask"}
    P = points[v, u].astype(np.float64)
    if not np.isfinite(P).all() or P[2] <= 1e-4:
        return {"ok": False, "reason": "invalid_foot_xyz"}
    if gravity is None:
        g = np.array([0.0, 1.0, 0.0])  # OpenCV Y-down
    else:
        g = np.asarray(gravity, dtype=np.float64).reshape(-1)[:3]
        n = np.linalg.norm(g)
        g = g / n if n > 1e-6 else np.array([0.0, 1.0, 0.0])
    head = P - actor_m * g
    foot_uv = _project_norm_K(K, P, w, h)
    head_uv = _project_norm_K(K, head, w, h)
    if foot_uv is None or head_uv is None:
        return {"ok": False, "reason": "projection_failed", "xyz": P.tolist()}
    height_px = abs(foot_uv[1] - head_uv[1])
    return {
        "ok": True,
        "foot_xyz": P.tolist(),
        "head_xyz": head.tolist(),
        "foot_reproj_px": [float(foot_uv[0]), float(foot_uv[1])],
        "head_reproj_px": [float(head_uv[0]), float(head_uv[1])],
        "height_px": float(height_px),
        "depth_m": float(P[2]),
        "camera_height_at_foot_m": float(abs(np.dot(P, g))),
    }


def _project_norm_K(
    K: np.ndarray, xyz: np.ndarray, w: int, h: int
) -> tuple[float, float] | None:
    X, Y, Z = [float(c) for c in xyz]
    if Z <= 1e-6:
        return None
    x, y = X / Z, Y / Z
    fx, fy, cx, cy = float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])
    # MoGe stores normalized intrinsics (fx relative to width).
    if 0.2 < fx < 5.0:
        u = (fx * x + cx) * w
        v = (fy * y + cy) * h
    else:
        u = fx * x + cx
        v = fy * y + cy
    return u, v


def evaluate_footpoint(
    *,
    name: str,
    zone: str,
    foot_xy: tuple[float, float],
    frame_wh: tuple[int, int],
    horizon_y: float,
    requested_height_px: float | None = None,
    moge_actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    w, h = frame_wh
    fx, fy = foot_xy
    classical = similar_triangles_height_px(fy, horizon_y)
    rng = height_range_px(fy, horizon_y)
    height = None
    source = "classical_similar_triangles"
    if moge_actor and moge_actor.get("ok") and moge_actor.get("height_px"):
        height = float(moge_actor["height_px"])
        source = "moge_metric_project"
    elif classical is not None:
        height = classical
    row: dict[str, Any] = {
        "name": name,
        "zone": zone,
        "foot_xy_px": [float(fx), float(fy)],
        "foot_xy_frac": [float(fx) / w, float(fy) / h],
        "footpoint_depth": zone,
        "classical_height_px": classical,
        "expected_height_range_px": list(rng) if rng else None,
        "expected_actor_height_px": height,
        "height_source": source,
        "moge": moge_actor,
    }
    if height is not None:
        row["expected_actor_bbox"] = project_actor_bbox((fx, fy), height, (w, h))
        row["expected_height_frac"] = float(height / h)
    if requested_height_px is not None and rng is not None:
        lo, hi = rng
        ok = lo <= requested_height_px <= hi
        row["requested_height_px"] = requested_height_px
        row["geometry_consistency"] = "PASS" if ok else "FAIL"
        if not ok:
            row["reason"] = (
                f"{zone} footpoint paired with requested {requested_height_px:.0f}px; "
                f"legal adult height at this depth is {lo:.0f}–{hi:.0f}px"
            )
    elif height is None:
        row["geometry_consistency"] = "FAIL"
        row["reason"] = "footpoint at or above horizon; not a ground contact"
    else:
        row["geometry_consistency"] = "MEASURED"
    return row


def layout_geometry_check(
    background_plate: str | Path,
    footpoints: list[dict[str, Any]],
    *,
    actor_height_m: float = ACTOR_HEIGHT_M,
    requested_height_px: float | None = None,
    device: str | None = None,
    use_moge: bool = True,
    use_geocalib: bool = True,
) -> dict[str, Any]:
    """Measure camera/ground and the legal actor bbox at each footpoint.

    Does not render characters. Does not APPROVE a shot.
    """
    path = Path(background_plate)
    rgb = _load_rgb(path)
    h, w = rgb.shape[:2]
    vp = detect_vanishing_point(rgb)
    horizon_y = float(vp["horizon_y"])
    backends: dict[str, Any] = {"classical_vp": {k: vp[k] for k in vp if k != "points"}}

    if device is None:
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    geocalib = _try_geocalib(rgb, device) if use_geocalib else {"ok": False, "error": "skipped"}
    backends["geocalib"] = {k: v for k, v in (geocalib or {}).items() if k != "image"}
    if geocalib and geocalib.get("ok") and geocalib.get("horizon_y") is not None:
        hy = float(geocalib["horizon_y"])
        if 0.05 * h < hy < 0.95 * h:
            horizon_y = hy
            backends["horizon_source"] = "geocalib"
        else:
            backends["horizon_source"] = "classical_vp_geocalib_out_of_frame"
    else:
        backends["horizon_source"] = "classical_vp"

    moge = _try_moge(rgb, device) if use_moge else {"ok": False, "error": "skipped"}
    moge_meta = None
    if moge and moge.get("ok"):
        moge_meta = {
            "ok": True,
            "backend": moge.get("backend"),
            "intrinsics": np.asarray(moge["intrinsics"]).tolist(),
            "fov": moge.get("fov"),
            "depth_valid_frac": float(np.mean(moge["mask"])) if moge.get("mask") is not None else None,
        }
        backends["moge"] = moge_meta
    else:
        backends["moge"] = moge

    gravity = None
    if geocalib and geocalib.get("ok") and geocalib.get("gravity"):
        try:
            gravity = np.array(geocalib["gravity"], dtype=np.float64).reshape(-1)[:3]
        except Exception:
            gravity = None

    rows = []
    for spec in footpoints:
        name = str(spec.get("name") or spec.get("zone") or "foot")
        zone = str(spec.get("zone") or name)
        frac = spec.get("xy_frac") or spec.get("feet_xy_frac")
        if frac is not None:
            fx, fy = float(frac[0]) * w, float(frac[1]) * h
        else:
            xy = spec.get("xy_px") or spec.get("feet_xy_px")
            fx, fy = float(xy[0]), float(xy[1])
        req = spec.get("requested_height_px", requested_height_px)
        moge_actor = None
        if moge and moge.get("ok"):
            moge_actor = moge_actor_at_foot(moge, (fx, fy), actor_height_m, gravity)
        rows.append(
            evaluate_footpoint(
                name=name,
                zone=zone,
                foot_xy=(fx, fy),
                frame_wh=(w, h),
                horizon_y=horizon_y,
                requested_height_px=req,
                moge_actor=moge_actor,
            )
        )

    fov_x = None
    if vp.get("vanishing_point_px"):
        # Rough pinhole FOV if principal point is frame center and fx ≈ vp geometry unused.
        fov_x = math.degrees(2 * math.atan((w / 2) / max(w * 0.8, 1)))
    report = {
        "schema_version": "layout-geometry-check/v0.1",
        "not_approval": True,
        "background_plate": str(path),
        "frame": [w, h],
        "actor_height_m": actor_height_m,
        "camera_height_m_assumed": CAMERA_HEIGHT_M,
        "camera_fov_deg_rough": fov_x,
        "horizon_y": horizon_y,
        "vanishing_point_px": vp.get("vanishing_point_px"),
        "gravity_direction": backends.get("geocalib", {}).get("gravity"),
        "floor_plane": "similar_triangles_plus_optional_moge_metric",
        "geometry_confidence": _confidence(vp, geocalib, moge),
        "backends": backends,
        "footpoints": rows,
    }
    return report


def _confidence(vp: dict[str, Any], geocalib: dict[str, Any] | None, moge: dict[str, Any] | None) -> float:
    score = 0.25
    if vp.get("ok"):
        score += 0.25
        score += min(0.2, 0.02 * int(vp.get("inliers") or 0))
    if geocalib and geocalib.get("ok"):
        score += 0.15
    if moge and moge.get("ok"):
        score += 0.2
    return round(min(score, 0.95), 2)


def draw_probe(
    background_plate: str | Path,
    report: dict[str, Any],
    dest: str | Path,
) -> Path:
    """Wireframe mannequins only. Not a character cel. Not a final still."""
    from PIL import Image, ImageDraw, ImageFont

    path = Path(background_plate)
    dest_path = Path(dest)
    im = Image.open(path).convert("RGB")
    overlay = im.copy()
    d = ImageDraw.Draw(overlay, "RGBA") if False else ImageDraw.Draw(overlay)
    w, h = im.size
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        small = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        small = font
    colors = {
        "left_foreground": (0, 200, 255),
        "left_midground": (255, 210, 40),
        "kitchen_background": (255, 80, 180),
        "a4_requested": (255, 60, 60),
    }
    hy = float(report["horizon_y"])
    d.line([(0, hy), (w, hy)], fill=(255, 140, 0), width=3)
    d.text((12, max(8, hy - 28)), "horizon", fill=(255, 140, 0), font=small)
    vp = report.get("vanishing_point_px") or [w / 2, hy]
    d.ellipse([vp[0] - 6, vp[1] - 6, vp[0] + 6, vp[1] + 6], outline=(255, 140, 0), width=3)
    for row in report.get("footpoints") or []:
        zone = row.get("zone") or row.get("name") or ""
        color = colors.get(zone, (180, 255, 180))
        fx, fy = row["foot_xy_px"]
        bbox = row.get("expected_actor_bbox")
        if bbox:
            d.rectangle(bbox, outline=color, width=3)
            _stick(d, bbox, color)
        d.ellipse([fx - 7, fy - 4, fx + 7, fy + 6], outline=color, width=3)
        d.line([(fx - 18, fy), (fx + 18, fy)], fill=color, width=2)
        hp = row.get("expected_actor_height_px")
        frac = row.get("expected_height_frac")
        label = f"{row.get('name')}  "
        if hp:
            label += f"{hp:.0f}px"
        if frac:
            label += f"  {frac*100:.0f}%"
        cons = row.get("geometry_consistency")
        if cons:
            label += f"  {cons}"
        tx, ty = fx + 12, (bbox[1] - 22) if bbox else fy - 24
        d.text((tx, max(4, ty)), label, fill=color, font=small)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(dest_path, quality=92)
    return dest_path


def _stick(draw: Any, bbox: list[int], color: tuple[int, int, int]) -> None:
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    h = y1 - y0
    head_r = max(4, int(h * 0.08))
    head_cy = y0 + head_r + 2
    hip = y0 + int(h * 0.55)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], outline=color, width=2)
    draw.line([(cx, head_cy + head_r), (cx, hip)], fill=color, width=2)
    draw.line([(x0 + 4, y0 + int(h * 0.28)), (x1 - 4, y0 + int(h * 0.28))], fill=color, width=2)
    draw.line([(cx, hip), (x0 + 6, y1)], fill=color, width=2)
    draw.line([(cx, hip), (x1 - 6, y1)], fill=color, width=2)


def write_report(path: Path, report: dict[str, Any]) -> None:
    slim = json.loads(json.dumps(report, default=str))
    # Drop giant arrays if any leaked.
    backends = slim.get("backends") or {}
    moge = backends.get("moge") or {}
    for k in ("points", "depth", "mask", "normal"):
        moge.pop(k, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
