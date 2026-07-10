import pytest

from app.engine import diagnose, fixing_shift_of
from app.suggestions import build_suggestions


def _f(cls, braces=None, profile=None, conf=0.9):
    return {
        "class": cls,
        "confidence": conf,
        "profile": profile,
        "braces": braces or [],
    }


def _b(cls, quality="correct", conf=0.8):
    return {"class": cls, "confidence": conf, "install_quality": quality}


def test_combo_requires_distinct_classes():
    shift, _ = fixing_shift_of([_b("brace_tension_rod"), _b("brace_tension_rod")])
    assert shift == -1

    shift, _ = fixing_shift_of([_b("brace_tension_rod"), _b("brace_stopper")])
    assert shift == -2

    shift, _ = fixing_shift_of([_b("brace_mat"), _b("brace_l_bracket")])
    assert shift == -1


def test_install_quality_affects_shift():
    shift, mods = fixing_shift_of([_b("brace_l_bracket", "loose")])
    assert shift == 0
    assert any(m["factor"].endswith("_loose") for m in mods)

    shift, mods = fixing_shift_of([_b("brace_l_bracket", "wrong_position")])
    assert shift == 0
    assert any(m["factor"] == "fix_wrong_position" for m in mods)

    shift, _ = fixing_shift_of([_b("brace_l_bracket", "unverified")])
    assert shift == 0


def test_modifiers_record_all_shifts():
    det = {
        "furniture": [_f("furniture_bookshelf", [_b("brace_l_bracket")])],
        "image_issues": [],
    }
    r = diagnose(det, "s6weak", "soft", "wood", 12, False)
    factors = {m["factor"] for m in r["results"][0]["risk"]["modifiers"]}
    assert "soil_soft" in factors
    assert "high_floor" in factors
    assert "fix_l_bracket_correct" in factors
    assert all(
        isinstance(m.get("label"), str) and m["label"]
        for m in r["results"][0]["risk"]["modifiers"]
    )


def test_display_block_is_human_readable():
    det = {"furniture": [_f("furniture_bookshelf")], "image_issues": []}
    r = diagnose(det, "s6strong", "normal", "wood", 1, False)
    d = r["results"][0]["display"]
    assert d["title"] == "本棚"
    assert d["headline"] == "転倒リスク：高"
    assert "本棚" in d["summary"]
    assert len(d["reason_chain"]) >= 1
    assert d["badge"]["label"] == "高"
    assert "bbox" not in d and "level" not in d.get("summary", "")


def test_unfixed_furniture_gets_l_bracket_and_stud_note():
    s = build_suggestions(_f("furniture_bookshelf"), [], 2, "topple", 1)
    actions = [x["action"] for x in s]
    assert "add_l_bracket" in actions
    assert actions[-1] == "stud_note"
    assert s[0]["action"] == "add_l_bracket"


def test_mat_only_on_heavy_furniture():
    braces = [_b("brace_mat")]
    s = build_suggestions(
        _f("furniture_wardrobe", braces, profile="chest"),
        braces,
        1,
        "topple",
        1,
    )
    actions = [x["action"] for x in s]
    assert "add_brace_with_mat" in actions
    assert "add_l_bracket" not in actions
    assert all("0%" not in x["text"] for x in s)


def test_wrong_position_is_top_priority():
    braces = [_b("brace_tension_rod", "wrong_position")]
    s = build_suggestions(_f("furniture_bookshelf", braces), braces, 2, "topple", 1)
    assert s[0]["action"] == "reposition"


def test_loose_triggers_retighten():
    braces = [_b("brace_l_bracket", "loose")]
    s = build_suggestions(_f("furniture_bookshelf", braces), braces, 1, "topple", 1)
    assert "retighten" in [x["action"] for x in s]


def test_slide_type_suggests_casters():
    s = build_suggestions(_f("furniture_bookshelf"), [], 1, "slide", 12)
    assert "secure_casters" in [x["action"] for x in s]


def test_other_class_only_gets_note():
    s = build_suggestions(_f("furniture_other"), [], 2, "topple", 1)
    assert [x["action"] for x in s] == ["out_of_scope_note"]


def test_max_three_plus_note():
    braces = [
        _b("brace_l_bracket", "loose"),
        _b("brace_tension_rod", "wrong_position"),
        _b("brace_mat", "unverified"),
    ]
    s = build_suggestions(_f("furniture_bookshelf", braces), braces, 2, "slide", 12)
    non_note = [x for x in s if x["action"] != "stud_note"]
    assert len(non_note) <= 3
