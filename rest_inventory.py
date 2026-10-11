import logging
import os
import time

from flask import Flask, jsonify, request


INVENTORY = {"sku-123": 7}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(PORT=int(os.environ.get("INVENTORY_REST_PORT", "5001")))
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="inventory")

    @app.get("/inventory/<item_id>")
    def check_inventory(item_id):
        try:
            quantity = int(request.args.get("quantity", "1"))
            delay_ms = int(request.args.get("delay_ms", "0"))
            if quantity <= 0 or delay_ms < 0 or delay_ms > 10000:
                raise ValueError
        except ValueError:
            return jsonify(error="invalid_request", service="inventory"), 400

        time.sleep(delay_ms / 1000)
        available_quantity = INVENTORY.get(item_id, 0)
        return jsonify(
            item_id=item_id,
            requested_quantity=quantity,
            available_quantity=available_quantity,
            available=available_quantity >= quantity,
            service="inventory",
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], threaded=True)
