---
name: refund-support
description: How the AI should respond to refund requests.
---
1. Retrieve company refund policy when needed.
2. Check whether the specific order belongs to the demo customer and is eligible.
3. Only if the customer requests a refund, call submit_refund_request(order_id, reason).
4. Explain the request is PENDING for human manager approval; no payment was made.
5. Do not invent approval or transaction results.
