import logging
import os
import time
from concurrent import futures

import grpc

from generated import inventory_pb2, inventory_pb2_grpc


INVENTORY = {"sku-123": 7}


class InventoryServicer(inventory_pb2_grpc.InventoryServiceServicer):
    def CheckInventory(self, request, context):
        if not request.item_id or request.quantity <= 0 or request.delay_ms < 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "item_id, quantity, and delay are invalid")
        time.sleep(request.delay_ms / 1000)
        available_quantity = INVENTORY.get(request.item_id, 0)
        return inventory_pb2.InventoryResponse(
            item_id=request.item_id,
            requested_quantity=request.quantity,
            available_quantity=available_quantity,
            available=available_quantity >= request.quantity,
        )


def serve():
    port = os.environ.get("INVENTORY_GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    logging.info("service=inventory protocol=grpc address=127.0.0.1:%s", port)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
