import logging
import os
import time

from flask import Flask, jsonify, request


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(PORT=int(os.environ.get("INVENTORY_PORT", "5001")))
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="inventory")

    @app.get("/v1/items/<item_id>")
    def get_item(item_id):
        request_id = request.headers.get("X-Request-ID", "none")
        try:
            delay_ms = int(request.args.get("delay_ms", "0"))
            if not 0 <= delay_ms <= 3000:
                raise ValueError
        except ValueError:
            return jsonify(error="invalid_delay", request_id=request_id), 400

        app.logger.info("request_id=%s event=started item_id=%s delay_ms=%s", request_id, item_id, delay_ms)
        time.sleep(delay_ms / 1000)

        if item_id != "sku-123":
            app.logger.info("request_id=%s event=finished status=404", request_id)
            return jsonify(error="item_not_found", request_id=request_id), 404

        app.logger.info("request_id=%s event=finished status=200", request_id)
        return jsonify(item_id=item_id, available=7, request_id=request_id), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], threaded=True)
