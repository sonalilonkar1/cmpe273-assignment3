import logging
import os
import time
import uuid

import requests
from flask import Flask, jsonify, request


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        INVENTORY_URL=os.environ.get("INVENTORY_REST_URL", "http://127.0.0.1:5001"),
        TIMEOUT=float(os.environ.get("REST_TIMEOUT", "0.6")),
        PORT=int(os.environ.get("ORDER_REST_PORT", "5000")),
    )
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="order")

    @app.get("/order/check-inventory")
    def order_check_inventory():
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        item_id = request.args.get("item_id", "sku-123")
        quantity_raw = request.args.get("quantity", "1")
        delay_ms = request.args.get("delay_ms", "0")
        started = time.monotonic()
        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
            response = requests.get(
                f"{app.config['INVENTORY_URL'].rstrip('/')}/inventory/{item_id}",
                params={"quantity": quantity, "delay_ms": delay_ms},
                headers={"X-Request-ID": request_id},
                timeout=app.config["TIMEOUT"],
            )
            if response.status_code == 400:
                body, status = {"error": "invalid_inventory_request"}, 400
            elif response.status_code != 200:
                body, status = {"error": "inventory_unavailable"}, 503
            else:
                data = response.json()
                body, status = {
                    "item_id": data["item_id"],
                    "quantity": data["requested_quantity"],
                    "available": data["available"],
                    "available_quantity": data["available_quantity"],
                }, 200
        except ValueError:
            body, status = {"error": "invalid_quantity"}, 400
        except requests.Timeout:
            body, status = {"error": "inventory_deadline_exceeded"}, 504
        except requests.RequestException:
            body, status = {"error": "inventory_unavailable"}, 503
        finally:
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            app.logger.info(
                "service=order protocol=rest request_id=%s status=%s latency_ms=%s",
                request_id,
                status,
                latency_ms,
            )

        result = jsonify(**body, service="order", request_id=request_id)
        result.status_code = status
        result.headers["X-Request-ID"] = request_id
        return result

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], threaded=True)
