import pytest

from app.engine import diagnose


def _furniture(
    cls: str,
    conf: float = 0.9,
    profile: str | None = None,
    braces: list | None = None,
) -> dict:
    return {
        "class": cls,
        "confidence": conf,
        "bbox": None,
        "profile": profile,
        "braces": braces or [],
    }


def _brace(
    cls: str,
    install_quality: str = "correct",
    conf: float = 0.8,
) -> dict:
    return {
        "class": cls,
        "confidence": conf,
        "install_quality": install_quality,
        "bbox": None,
    }


def test_primary_index_is_zero():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["primary_index"] == 0


def test_physics_mid_reason_chain_explains_margin():
    detection = {"furniture": [_furniture("furniture_cupboard")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    item = result["results"][0]
    assert item["risk"]["level"] == "mid"
    first = item["display"]["reason_chain"][0]
    assert "1ガル＝1cm/s²" in first
    assert "162.4" in first
    assert "中" in first


def test_physics_low_reason_chain_includes_gal_unit():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s5weak", "normal", "wood", 1, False)
    item = result["results"][0]
    assert item["risk"]["level"] == "low"
    first = item["display"]["reason_chain"][0]
    assert "1ガル＝1cm/s²" in first
    assert "低" in first


def test_physics_high_reason_chain_includes_ar50():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6strong", "normal", "wood", 1, False)
    item = result["results"][0]
    assert item["risk"]["level"] == "high"
    first = item["display"]["reason_chain"][0]
    assert "1ガル＝1cm/s²" in first
    assert "205" in first
    assert "高" in first


def test_stat_track_reason_chain_mentions_tfd_and_rate():
    detection = {"furniture": [_furniture("furniture_tv")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    chain = " ".join(result["results"][0]["display"]["reason_chain"])
    assert "38.2%" in chain
    assert "東京消防庁" in chain


def test_sources_physics_unfixed_includes_nilim_jma_tfd_h_not_tfd_m():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    ids = {s["id"] for s in result["sources"]}
    assert ids == {"NILIM", "JMA", "TFD-H"}


def test_sources_stat_track_includes_tfd_h():
    detection = {"furniture": [_furniture("furniture_tv")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    ids = {s["id"] for s in result["sources"]}
    assert "TFD-H" in ids
    assert "JMA" in ids
    assert "NILIM" not in ids


def test_sources_combo_includes_tfd_m():
    detection = {
        "furniture": [
            _furniture(
                "furniture_bookshelf",
                braces=[_brace("brace_tension_rod"), _brace("brace_stopper")],
            )
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    ids = {s["id"] for s in result["sources"]}
    assert "TFD-M" in ids


def test_sources_summary_has_no_absolute_claims():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    for source in result["sources"]:
        assert "0%" not in source["summary"]
        assert "絶対" not in source["summary"]


def test_results_still_returns_all_furniture():
    detection = {
        "furniture": [
            _furniture("furniture_tv"),
            _furniture("furniture_bookshelf"),
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6strong", "normal", "wood", 1, False)
    assert len(result["results"]) == 2
