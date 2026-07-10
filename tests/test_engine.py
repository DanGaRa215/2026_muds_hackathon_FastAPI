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


def test_t1_bookshelf_s6weak_unfixed_mid():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["status"] == "ok"
    assert result["results"][0]["risk"]["level"] == "mid"


def test_t2_bookshelf_s6strong_unfixed_high():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6strong", "normal", "wood", 1, False)
    assert result["results"][0]["risk"]["level"] == "high"


def test_t3_bookshelf_s6weak_l_bracket_low():
    detection = {
        "furniture": [
            _furniture("furniture_bookshelf", braces=[_brace("brace_l_bracket")])
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["results"][0]["risk"]["level"] == "low"
    assert result["results"][0]["risk"]["base_level"] == "mid"


def test_t4_cupboard_s7_base_isolated_slide():
    detection = {"furniture": [_furniture("furniture_cupboard")], "image_issues": []}
    result = diagnose(detection, "s7", "normal", "wood", 8, True)
    risk = result["results"][0]["risk"]
    assert risk["level"] == "mid"
    assert risk["type"] == "slide"


def test_t5_wardrobe_chest_soft_soil_mid():
    detection = {
        "furniture": [_furniture("furniture_wardrobe", profile="chest")],
        "image_issues": [],
    }
    result = diagnose(detection, "s6weak", "soft", "wood", 1, False)
    assert result["results"][0]["risk"]["level"] == "mid"


def test_t6_tv_s6weak_unfixed_mid():
    detection = {"furniture": [_furniture("furniture_tv")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["results"][0]["risk"]["level"] == "mid"


def test_t7_tv_s5strong_unfixed_low():
    detection = {"furniture": [_furniture("furniture_tv")], "image_issues": []}
    result = diagnose(detection, "s5strong", "normal", "wood", 1, False)
    assert result["results"][0]["risk"]["level"] == "low"


def test_t8_wardrobe_mat_only_warning():
    detection = {
        "furniture": [
            _furniture(
                "furniture_wardrobe",
                profile="chest",
                braces=[_brace("brace_mat")],
            )
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6strong", "normal", "wood", 1, False)
    item = result["results"][0]
    assert item["risk"]["level"] == "mid"
    assert "mat_ineffective_on_heavy" in item["warnings"]
    assert item["suggestions"]


def test_t9_bookshelf_high_floor_combo_shift():
    detection = {
        "furniture": [
            _furniture(
                "furniture_bookshelf",
                braces=[
                    _brace("brace_tension_rod"),
                    _brace("brace_stopper"),
                ],
            )
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6strong", "normal", "wood", 12, False)
    item = result["results"][0]
    assert item["risk"]["level"] == "mid"
    assert "slide_on_high_floor" in item["warnings"]


def test_t10_low_conf_furniture_retake():
    detection = {
        "furniture": [
            _furniture("furniture_bookshelf", conf=0.4, braces=[_brace("brace_l_bracket", conf=0.9)])
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["status"] == "retake"
    assert result["reason"] == "brace_only"


def test_no_furniture_image_issue():
    detection = {"furniture": [], "image_issues": ["no_furniture"]}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result == {"status": "retake", "reason": "no_furniture"}


def test_furniture_other_out_of_scope():
    detection = {"furniture": [_furniture("furniture_other")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    assert result["results"][0]["out_of_scope"] is True
    assert result["results"][0]["risk"] is None


def test_results_sorted_high_to_low():
    detection = {
        "furniture": [
            _furniture("furniture_tv"),
            _furniture("furniture_bookshelf"),
        ],
        "image_issues": [],
    }
    result = diagnose(detection, "s6strong", "normal", "wood", 1, False)
    levels = [item["risk"]["level"] for item in result["results"]]
    assert levels == sorted(levels, key={"low": 0, "mid": 1, "high": 2}.get, reverse=True)


def test_response_includes_input_echo():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    result = diagnose(detection, "s6weak", "normal", "rc", 3, True)
    assert result["input"] == {
        "shindo": "s6weak",
        "soil": "normal",
        "structure": "rc",
        "floor_no": 3,
        "base_isolated": True,
    }


def test_structure_does_not_change_risk_level():
    detection = {"furniture": [_furniture("furniture_bookshelf")], "image_issues": []}
    wood = diagnose(detection, "s6weak", "normal", "wood", 1, False)
    rc = diagnose(detection, "s6weak", "normal", "rc", 1, False)
    assert wood["results"][0]["risk"]["level"] == rc["results"][0]["risk"]["level"]

