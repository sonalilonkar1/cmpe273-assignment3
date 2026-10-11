# Assignment Evidence

The following outputs were captured from local runs. Replace or supplement them with terminal screenshots before submitting if your instructor requires visual evidence.

## Automated tests

```text
........                                                                 [100%]
8 passed in 0.24s
```

## REST success

```text
HTTP/1.1 200 OK
{"available":true,"available_quantity":7,"item_id":"sku-123","quantity":2,"service":"order"}
```

## REST timeout and Order survival

```text
HTTP/1.1 504 GATEWAY TIMEOUT
{"error":"inventory_deadline_exceeded","service":"order"}

HTTP/1.1 200 OK
{"service":"order","status":"ok"}
```

The Inventory delay was 2000 ms and the REST timeout was 600 ms.

## gRPC success through the Order API

```text
HTTP/1.1 200 OK
{"available":true,"available_quantity":7,"item_id":"sku-123","protocol":"grpc","quantity":2,"service":"order"}
```

## gRPC deadline and Order survival

```text
HTTP/1.1 504 GATEWAY TIMEOUT
{"error":"inventory_deadline_exceeded","protocol":"grpc","service":"order"}

HTTP/1.1 200 OK
{"protocol":"grpc","service":"order","status":"ok"}
```

The Inventory delay was 2000 ms and the gRPC deadline was 600 ms.

## Failure interpretation

The `504` responses show that the Order service converts a REST read timeout or gRPC `DEADLINE_EXCEEDED` into a controlled response. The health responses show that the Order service process continues running after either failure. When Inventory is stopped completely, the expected controlled response is `503 inventory_unavailable`; restarting Inventory restores successful calls.
