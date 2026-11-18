
import pytest
from fastapi.testclient import TestClient

from backend.app.database import initialize_database
from backend.app.main import app, get_connection


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_continuityproof.db"

    initialize_database(test_database)

    def override_get_connection():
        return get_connection(test_database)

    monkeypatch.setattr(
        "backend.app.main.get_connection",
        override_get_connection
    )

    with TestClient(app) as test_client:
        yield test_client


def test_homepage(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["product"] == "ContinuityProof AI"


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_assets(client):
    response = client.get("/assets")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json() == []

def test_register_asset(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-TEST01",
        "operating_system": "Windows Server 2022",
        "environment": "development"
    }

    response = client.post("/assets", json=asset_data)

    assert response.status_code == 201
    assert response.json()["asset_name"] == "NovaSol Test Server"
    assert response.json()["hostname"] == "NS-TEST01"


def test_duplicate_hostname_rejected(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-TEST01",
        "operating_system": "Windows Server 2022",
        "environment": "development"
    }

    first_response = client.post("/assets", json=asset_data)
    second_response = client.post("/assets", json=asset_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_get_nonexistent_asset(client):
    response = client.get("/assets/999")

    assert response.status_code == 404

def test_update_asset(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-TEST01",
        "operating_system": "Windows Server 2022",
        "environment": "development"
    }

    create_response = client.post("/assets", json=asset_data)

    asset_id = create_response.json()["id"]

    updated_data = {
        "asset_name": "NovaSol Updated Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-TEST01",
        "operating_system": "Windows Server 2022",
        "environment": "production"
    }

    update_response = client.put(
        f"/assets/{asset_id}",
        json=updated_data
    )

    assert update_response.status_code == 200
    assert update_response.json()["asset_name"] == "NovaSol Updated Test Server"
    assert update_response.json()["environment"] == "production"


def test_delete_asset(client):
    asset_data = {
        "asset_name": "NovaSol Temporary Server",
        "asset_type": "Linux Server",
        "hostname": "NS-TEMP01",
        "operating_system": "Ubuntu",
        "environment": "development"
    }

    create_response = client.post("/assets", json=asset_data)

    asset_id = create_response.json()["id"]

    delete_response = client.delete(f"/assets/{asset_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Asset deleted successfully."

    get_response = client.get(f"/assets/{asset_id}")

    assert get_response.status_code == 404

def test_reject_blank_asset_name(client):
    asset_data = {
        "asset_name": "   ",
        "asset_type": "Windows Server",
        "hostname": "NS-BLANK01",
        "operating_system": "Windows Server 2022",
        "environment": "development"
    }

    response = client.post("/assets", json=asset_data)

    assert response.status_code == 422


def test_reject_blank_asset_type(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "   ",
        "hostname": "NS-BLANK02",
        "operating_system": "Windows Server 2022",
        "environment": "development"
    }

    response = client.post("/assets", json=asset_data)

    assert response.status_code == 422


def test_reject_invalid_environment(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-INVALID01",
        "operating_system": "Windows Server 2022",
        "environment": "production-like"
    }

    response = client.post("/assets", json=asset_data)

    assert response.status_code == 422


def test_normalize_environment_to_lowercase(client):
    asset_data = {
        "asset_name": "NovaSol Test Server",
        "asset_type": "Windows Server",
        "hostname": "NS-UPPER01",
        "operating_system": "Windows Server 2022",
        "environment": "PRODUCTION"
    }

    response = client.post("/assets", json=asset_data)

    assert response.status_code == 201
    assert response.json()["environment"] == "production"
