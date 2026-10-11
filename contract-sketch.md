# Inventory API Contract Sketch

## `GET /v1/items/{item_id}`

Purpose: read current availability. This does not reserve stock.

Successful response (`200`):

```json
{
  "item_id": "sku-123",
  "available": 7,
  "request_id": "<correlation-id>"
}
```

Errors:

- `400 invalid_delay`: request parameter is invalid.
- `404 item_not_found`: item does not exist.
- `503 dependency_unavailable`: checkout cannot reach inventory.
- `504 dependency_timeout`: inventory did not respond before the read timeout.
- `502 dependency_bad_response`: inventory returned an invalid or unexpected response.

Identity and authorization for production: verify the caller's authenticated service identity and require `inventory.read`. The local exercise uses loopback HTTP only and intentionally has no authentication.

## Failure semantics

`available: 0` is a valid business result, not a transport failure. A timeout does not prove that the inventory operation did not execute. State-changing endpoints would require an idempotency key and outcome lookup before retrying.
