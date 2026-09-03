def test_foreground_small_actor_is_illegal() -> None:
    """A4 22% at a near-camera foot cannot pass similar-triangles."""
    from lib.layout_geometry import height_range_px, similar_triangles_height_px

    horizon_y = 360.0
    foot_y = 651.0
    requested = 158.0
    expected = similar_triangles_height_px(foot_y, horizon_y, actor_m=1.75, camera_m=1.55)
    lo, hi = height_range_px(foot_y, horizon_y)
    assert expected is not None
    assert expected > 250
    assert not (lo <= requested <= hi)


def test_midground_22pct_can_be_legal() -> None:
    from lib.layout_geometry import height_range_px

    # 22% of 720 ≈ 158px needs ~140px below a mid-frame horizon, not foreground.
    lo, hi = height_range_px(500.0, 360.0)
    assert lo <= 158.0 <= hi


if __name__ == "__main__":
    test_foreground_small_actor_is_illegal()
    test_midground_22pct_can_be_legal()
    print("ok")
