import io

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_SHARED_SECRET", "test-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    return TestClient(app)


def _multipart_payload(**overrides):
    data = {
        "shindo": "s6weak",
        "soil": "normal",
        "structure": "wood",
        "floor_no": "1",
        "base_isolated": "false",
    }
    data.update(overrides)
    return data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diagnose_unauthorized(client):
    response = client.post(
        "/diagnose",
        data=_multipart_payload(),
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
    )
    assert response.status_code == 401


def test_diagnose_invalid_key(client):
    response = client.post(
        "/diagnose",
        data=_multipart_payload(),
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_diagnose_image_too_large(client):
    large_image = b"x" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/diagnose",
        data=_multipart_payload(),
        files={"image": ("test.jpg", large_image, "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 413


def test_diagnose_success_with_mocked_vision(client, monkeypatch):
    def fake_vision_detect(image_bytes, content_type=None):
        return {
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

    monkeypatch.setattr("main.vision_detect", fake_vision_detect)

    response = client.post(
        "/diagnose",
        data=_multipart_payload(),
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["results"][0]["risk"]["level"] == "mid"
    assert "unknowns" in body


def test_diagnose_vision_parse_failure(client, monkeypatch):
    from app.vision import VisionDetectionError

    def fake_vision_detect(image_bytes, content_type=None):
        raise VisionDetectionError("parse failed")

    monkeypatch.setattr("app.vision.vision_detect", fake_vision_detect)

    response = client.post(
        "/diagnose",
        data=_multipart_payload(),
        files={"image": ("test.jpg", b"fake-image", "image/jpeg")},
        headers={"X-App-Key": "test-secret"},
    )
    assert response.status_code == 502
    assert response.json() == {"status": "api_error"}
