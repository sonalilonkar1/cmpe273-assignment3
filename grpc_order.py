import logging
import os
import time
import uuid

import grpc
from flask import Flask, jsonify, request

from generated import inventory_pb2, inventory_pb2_grpc


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        INVENTORY_GRPC_TARGET=os.environ.get("INVENTORY_GRPC_TARGET", "127.0.0.1:50051"),
        DEADLINE=float(os.environ.get("GRPC_DEADLINE", "0.6")),
        PORT=int(os.environ.get("ORDER_GRPC_PORT", "5002")),
    )
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="order", protocol="grpc")

    @app.get("/order/check-inventory")
    def order_check_inventory():
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        try:
            quantity = int(request.args.get("quantity", "1"))
            delay_ms = int(request.args.get("delay_ms", "0"))
            item_id = request.args.get("item_id", "sku-123")
            if quantity <= 0 or delay_ms < 0:
                raise ValueError
        except ValueError:
            return jsonify(error="invalid_request", service="order", request_id=request_id), 400

        started = time.monotonic()
        status = 200
        try:
            with grpc.insecure_channel(app.config["INVENTORY_GRPC_TARGET"]) as channel:
                stub = inventory_pb2_grpc.InventoryServiceStub(channel)
                response = stub.CheckInventory(
                    inventory_pb2.InventoryRequest(
                        item_id=item_id, quantity=quantity, delay_ms=delay_ms
                    ),
                    timeout=app.config["DEADLINE"],
                )
                body = {
                    "item_id": response.item_id,
                    "quantity": response.requested_quantity,
                    "available": response.available,
                    "available_quantity": response.available_quantity,
                }
        except grpc.RpcError as error:
            if error.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                body, status = {"error": "inventory_deadline_exceeded"}, 504
            elif error.code() == grpc.StatusCode.INVALID_ARGUMENT:
                body, status = {"error": "invalid_inventory_request"}, 400
            elif error.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.NOT_FOUND):
                body, status = {"error": "inventory_unavailable"}, 503
            else:
                body, status = {"error": "grpc_dependency_error"}, 502
        finally:
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            app.logger.info(
                "service=order protocol=grpc request_id=%s status=%s latency_ms=%s",
                request_id,
                status,
                latency_ms,
            )

        result = jsonify(**body, service="order", protocol="grpc", request_id=request_id)
        result.status_code = status
        result.headers["X-Request-ID"] = request_id
        return result

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], threaded=True)
