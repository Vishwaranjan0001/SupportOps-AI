"""MCP Server = the TOOL SERVER. The model never accesses SQLite directly."""
import json
import sys
from mcp.server import MCPServer
from db import (DEMO_CUSTOMER, init_db, get_order, list_orders, list_tickets,
                create_ticket, request_refund, list_refunds)

mcp = MCPServer('SupportOps tools')


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Find an order by ID and return its real status, product and delivery date."""
    order = get_order(order_id, DEMO_CUSTOMER)
    return json.dumps(order if order else {'error': 'Order not found or access denied'})


@mcp.tool()
def list_my_orders() -> str:
    """List orders belonging to the current demonstration customer."""
    return json.dumps(list_orders(DEMO_CUSTOMER))


@mcp.tool()
def check_refund_eligibility(order_id: str) -> str:
    """Check whether the database marks this customer's order refundable. Does not create refund."""
    order = get_order(order_id, DEMO_CUSTOMER)
    if not order:
        return json.dumps({'error': 'Order not found or access denied'})
    return json.dumps({'order_id': order_id, 'eligible': bool(order['refund_eligible']),
                       'note': 'Eligibility only. Policy may impose additional conditions.'})


@mcp.tool()
def create_support_ticket(subject: str, description: str, order_id: str = '') -> str:
    """Create an OPEN support ticket about an issue. order_id may be empty if general."""
    return json.dumps(create_ticket(order_id, subject, description, DEMO_CUSTOMER))


@mcp.tool()
def list_my_tickets() -> str:
    """Get this customer's previously opened support tickets and their statuses."""
    return json.dumps(list_tickets(DEMO_CUSTOMER))


@mcp.tool()
def submit_refund_request(order_id: str, reason: str) -> str:
    """Request a DEMO refund for manager review. Does NOT approve or pay a refund."""
    return json.dumps(request_refund(order_id, reason, DEMO_CUSTOMER))


@mcp.tool()
def list_my_refund_requests() -> str:
    """See whether a refund request is PENDING, APPROVED or REJECTED."""
    return json.dumps(list_refunds(DEMO_CUSTOMER))


if __name__ == '__main__':
    init_db()
    print('[MCP] SQLite tools ready', file=sys.stderr)  # No stdout! MCP uses stdout.
    mcp.run()
