import json

import pytest
from fastapi.testclient import TestClient

from app.parser import validate_schema
from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_SHARED_SECRET", "test-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    return TestClient(app)


def _multipart_payload(**overrides):
    data = {
        "structure": "wood",
        "floor_no": "1",
        "base_isolated": "false",
    }
    data.update(overrides)
    return data


def _valid_detection(**overrides) -> dict:
    base = {
        "furniture": [
            {
                "class": "furniture_bookshelf",
                "confidence": 0.9,
                "bbox": None,
                "profile": None,
                "braces": [],
            }
        ],
        "image_issues": [],
    }
    base.update(overrides)
    return base


def test_validate_schema_rejects_invalid_furniture_class():
    det = _valid_detection()
    det["furniture"][0]["class"] = "furniture_sofa"
    ok, reason = validate_schema(det)
    assert not ok
    assert "invalid_furniture_class" in reason


def test_detect_unauthorized(client):
    response = client.post(
        "/detect",
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
    )
    assert response.status_code == 401


def test_detect_ok_with_mocked_vision(client, monkeypatch):
    def fake_vision_detect(image_bytes, content_type=None):
        return _valid_detection()

    monkeypatch.setattr("main.vision_detect", fake_vision_detect)

    response = client.post(
        "/detect",
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["detection"]["furniture"][0]["class"] == "furniture_bookshelf"


def test_detect_retake_nothing_detected(client, monkeypatch):
    def fake_vision_detect(image_bytes, content_type=None):
        return {"furniture": [], "image_issues": []}

    monkeypatch.setattr("main.vision_detect", fake_vision_detect)

    response = client.post(
        "/detect",
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "retake", "reason": "nothing_detected"}


def test_diagnose_from_detection_skips_vision(client, monkeypatch):
    calls = {"count": 0}

    def fake_vision_detect(image_bytes, content_type=None):
        calls["count"] += 1
        return _valid_detection()

    monkeypatch.setattr("main.vision_detect", fake_vision_detect)

    response = client.post(
        "/diagnose",
        data=_multipart_payload(
            detection=json.dumps(_valid_detection()),
        ),
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls["count"] == 0


def test_diagnose_rejects_image_and_detection(client, monkeypatch):
    monkeypatch.setattr("main.vision_detect", lambda *a, **k: _valid_detection())

    response = client.post(
        "/diagnose",
        data=_multipart_payload(detection=json.dumps(_valid_detection())),
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 400


def test_diagnose_rejects_invalid_detection_class(client):
    det = _valid_detection()
    det["furniture"][0]["class"] = "furniture_sofa"

    response = client.post(
        "/diagnose",
        data=_multipart_payload(detection=json.dumps(det)),
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 400
    assert "invalid detection" in response.json()["detail"]


def test_diagnose_rejects_oversized_detection(client):
    huge = json.dumps(_valid_detection()) + (" " * (64 * 1024 + 1))

    response = client.post(
        "/diagnose",
        data=_multipart_payload(detection=huge),
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 400


def test_user_declared_unverified_brace_does_not_reduce_risk(client):
    det = _valid_detection()
    det["furniture"][0]["braces"] = [
        {
            "class": "brace_l_bracket",
            "confidence": 1.0,
            "install_quality": "unverified",
            "bbox": None,
        }
    ]

    response = client.post(
        "/diagnose",
        data=_multipart_payload(detection=json.dumps(det)),
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 200
    item = response.json()["results"][0]
    modifiers = item["risk"]["modifiers"]
    assert any(m["factor"] == "fix_unverified" for m in modifiers)
    assert item["risk"]["level"] == "mid"
