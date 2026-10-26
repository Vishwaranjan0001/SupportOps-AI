---
name: order-support
description: How the AI should respond to order and shipping questions.
---
1. Look up actual order information with get_order_status or list_my_orders.
2. Never guess the shipping status of a specific order.
3. If company shipping rules are relevant, use search_company_policy.
4. If the customer reports a persistent problem, offer to create a ticket.
