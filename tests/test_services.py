import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_app(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = load_app("inventory", ROOT / "inventory.py")
checkout = load_app("checkout", ROOT / "checkout.py")


def test_inventory_success_and_missing_item():
    client = inventory.create_app().test_client()
    success = client.get("/v1/items/sku-123")
    missing = client.get("/v1/items/missing")
    assert success.status_code == 200
    assert success.get_json()["available"] == 7
    assert missing.status_code == 404


def test_inventory_rejects_invalid_delay():
    response = inventory.create_app().test_client().get("/v1/items/sku-123?delay_ms=bad")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_delay"


def test_checkout_maps_dependency_success(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"item_id": "sku-123", "available": 7}

    monkeypatch.setattr(checkout.requests, "get", lambda *args, **kwargs: Response())
    response = checkout.create_app().test_client().get("/v1/availability/sku-123")
    assert response.status_code == 200
    assert response.get_json()["available"] == 7
    assert response.headers["X-Request-ID"]


def test_checkout_maps_timeout_to_504(monkeypatch):
    monkeypatch.setattr(checkout.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(checkout.requests.Timeout()))
    response = checkout.create_app().test_client().get("/v1/availability/sku-123")
    assert response.status_code == 504
    assert response.get_json()["error"] == "dependency_timeout"


def test_checkout_maps_connection_failure_to_503(monkeypatch):
    monkeypatch.setattr(
        checkout.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(checkout.requests.ConnectionError()),
    )
    response = checkout.create_app().test_client().get("/v1/availability/sku-123")
    assert response.status_code == 503
    assert response.get_json()["error"] == "dependency_unavailable"
