from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


ACTIVITY_NAME = "Test Activity"
STUDENT_EMAIL = "student@example.com"
EXISTING_EMAIL = "existing@example.com"


@pytest.fixture
def client(monkeypatch):
    # Arrange: give every test an isolated in-memory activity database.
    monkeypatch.setattr(
        app_module,
        "activities",
        {
            ACTIVITY_NAME: {
                "description": "A test activity",
                "schedule": "Mondays at 3:00 PM",
                "max_participants": 2,
                "participants": [EXISTING_EMAIL],
            }
        },
    )
    return TestClient(app_module.app)


def activity_signup_url():
    return f"/activities/{quote(ACTIVITY_NAME, safe='')}/signup"


def test_get_activities_returns_data_without_caching(client):
    # Arrange
    expected_activity = {
        "description": "A test activity",
        "schedule": "Mondays at 3:00 PM",
        "max_participants": 2,
        "participants": [EXISTING_EMAIL],
    }

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {ACTIVITY_NAME: expected_activity}
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_student(client):
    # Arrange
    url = activity_signup_url()

    # Act
    response = client.post(url, params={"email": STUDENT_EMAIL})

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {STUDENT_EMAIL} for {ACTIVITY_NAME}"
    }
    assert STUDENT_EMAIL in app_module.activities[ACTIVITY_NAME]["participants"]


def test_signup_rejects_duplicate_student(client):
    # Arrange
    url = activity_signup_url()

    # Act
    response = client.post(url, params={"email": EXISTING_EMAIL})

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert app_module.activities[ACTIVITY_NAME]["participants"] == [EXISTING_EMAIL]


def test_signup_rejects_unknown_activity(client):
    # Arrange
    url = "/activities/Unknown%20Activity/signup"

    # Act
    response = client.post(url, params={"email": STUDENT_EMAIL})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_removes_student(client):
    # Arrange
    url = activity_signup_url()
    email = EXISTING_EMAIL

    # Act
    response = client.delete(url, params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {ACTIVITY_NAME}"
    }
    assert email not in app_module.activities[ACTIVITY_NAME]["participants"]


def test_unregister_rejects_student_not_signed_up(client):
    # Arrange
    url = activity_signup_url()

    # Act
    response = client.delete(url, params={"email": STUDENT_EMAIL})

    # Assert
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }
    assert app_module.activities[ACTIVITY_NAME]["participants"] == [EXISTING_EMAIL]


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    url = "/activities/Unknown%20Activity/signup"

    # Act
    response = client.delete(url, params={"email": EXISTING_EMAIL})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
