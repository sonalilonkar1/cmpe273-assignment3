import logging
import os
import time
import uuid

import requests
from flask import Flask, jsonify, request


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        INVENTORY_URL=os.environ.get("INVENTORY_URL", "http://127.0.0.1:5001"),
        CONNECT_TIMEOUT=float(os.environ.get("CONNECT_TIMEOUT", "0.2")),
        READ_TIMEOUT=float(os.environ.get("READ_TIMEOUT", "0.6")),
        PORT=int(os.environ.get("CHECKOUT_PORT", "5000")),
    )
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="checkout")

    @app.get("/v1/availability/<item_id>")
    def availability(item_id):
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        status = 500
        body = {"error": "internal_error"}
        try:
            response = requests.get(
                f"{app.config['INVENTORY_URL'].rstrip('/')}/v1/items/{item_id}",
                params={"delay_ms": request.args.get("delay_ms", "0")},
                headers={"X-Request-ID": request_id},
                timeout=(app.config["CONNECT_TIMEOUT"], app.config["READ_TIMEOUT"]),
                allow_redirects=False,
            )
            if response.status_code == 404:
                body, status = {"error": "item_not_found"}, 404
            elif response.status_code == 400:
                body, status = {"error": "invalid_delay"}, 400
            elif response.status_code != 200:
                body, status = {"error": "dependency_bad_response"}, 502
            else:
                data = response.json()
                if (
                    not isinstance(data, dict)
                    or data.get("item_id") != item_id
                    or type(data.get("available")) is not int
                    or data["available"] < 0
                ):
                    raise ValueError("invalid inventory representation")
                body, status = {"item_id": item_id, "available": data["available"]}, 200
        except requests.Timeout:
            body, status = {"error": "dependency_timeout"}, 504
        except ValueError:
            body, status = {"error": "dependency_bad_response"}, 502
        except requests.RequestException:
            body, status = {"error": "dependency_unavailable"}, 503
        finally:
            elapsed_ms = round((time.monotonic() - started) * 1000, 1)
            app.logger.info(
                "request_id=%s endpoint=/v1/availability/%s status=%s elapsed_ms=%s",
                request_id,
                item_id,
                status,
                elapsed_ms,
            )

        result = jsonify(**body, request_id=request_id)
        result.status_code = status
        result.headers["X-Request-ID"] = request_id
        return result

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], threaded=True)
