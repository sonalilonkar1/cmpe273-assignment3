from concurrent import futures

import grpc
import pytest

from generated import inventory_pb2_grpc
from grpc_inventory import InventoryServicer
from grpc_order import create_app as create_grpc_order_app
from rest_order import create_app as create_rest_order_app


@pytest.fixture()
def grpc_inventory_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    yield f"127.0.0.1:{port}"
    server.stop(0)


def test_rest_success_and_timeout(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {
                "item_id": "sku-123",
                "requested_quantity": 2,
                "available_quantity": 7,
                "available": True,
            }

    def fake_get(*args, **kwargs):
        assert kwargs["timeout"] == 0.1
        return Response()

    monkeypatch.setattr("rest_order.requests.get", fake_get)
    client = create_rest_order_app({"TIMEOUT": 0.1}).test_client()
    response = client.get("/order/check-inventory?item_id=sku-123&quantity=2")
    assert response.status_code == 200
    assert response.get_json()["available"] is True


def test_grpc_success_and_health(grpc_inventory_server):
    app = create_grpc_order_app(
        {"INVENTORY_GRPC_TARGET": grpc_inventory_server, "DEADLINE": 0.5}
    )
    client = app.test_client()
    response = client.get("/order/check-inventory?item_id=sku-123&quantity=2")
    assert response.status_code == 200
    assert response.get_json()["available"] is True
    assert client.get("/health").status_code == 200


def test_grpc_deadline_does_not_kill_order(grpc_inventory_server):
    app = create_grpc_order_app(
        {"INVENTORY_GRPC_TARGET": grpc_inventory_server, "DEADLINE": 0.05}
    )
    client = app.test_client()
    response = client.get(
        "/order/check-inventory?item_id=sku-123&quantity=2&delay_ms=2000"
    )
    assert response.status_code == 504
    assert response.get_json()["error"] == "inventory_deadline_exceeded"
    assert client.get("/health").status_code == 200
