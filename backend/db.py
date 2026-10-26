"""All business data for the demo. SQLite is a single file; no database server needed."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DB_PATH = DATA / 'supportops.db'
DEMO_CUSTOMER = 'cust-001'  # Demo only; replace with authenticated user identity in production.


@contextmanager
def connect():
    """Commit or roll back each operation, then release the SQLite file handle."""
    DATA.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def init_db():
    """Create tables and fictional demo records on first launch."""
    with connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
                product TEXT NOT NULL, status TEXT NOT NULL,
                delivered_on TEXT, refund_eligible INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL, order_id TEXT,
                subject TEXT NOT NULL, description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN'
            );
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL, order_id TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
                UNIQUE(customer_id, order_id)
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL
            );
        ''')
        db.execute('INSERT OR IGNORE INTO customers VALUES (?, ?)', (DEMO_CUSTOMER, 'Demo Customer'))
        db.execute('INSERT OR IGNORE INTO customers VALUES (?, ?)', ('cust-002', 'Another Customer'))
        samples = [
            ('ORD-1001', DEMO_CUSTOMER, 'Wireless Headphones', 'SHIPPED', None, 0),
            ('ORD-1003', DEMO_CUSTOMER, 'Laptop Stand', 'DELIVERED', '2026-10-19', 1),
            ('ORD-1004', DEMO_CUSTOMER, 'Bluetooth Speaker', 'PROCESSING', None, 0),
            ('ORD-1002', 'cust-002', 'Gaming Mouse', 'DELIVERED', '2026-10-18', 1),
        ]
        db.executemany('INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?)', samples)


def list_orders(customer_id=DEMO_CUSTOMER):
    with connect() as db:
        return rows(db.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY id', (customer_id,)))


def get_order(order_id, customer_id=DEMO_CUSTOMER):
    with connect() as db:
        row = db.execute('SELECT * FROM orders WHERE id=? AND customer_id=?', (order_id, customer_id)).fetchone()
        return dict(row) if row else None


def create_ticket(order_id, subject, description, customer_id=DEMO_CUSTOMER):
    if order_id and not get_order(order_id, customer_id):
        return {'error': 'Order not found or access denied'}
    with connect() as db:
        cursor = db.execute('INSERT INTO tickets(customer_id, order_id, subject, description) VALUES (?,?,?,?)',
                            (customer_id, order_id or None, subject[:120], description[:1000]))
        return {'ticket_id': cursor.lastrowid, 'status': 'OPEN', 'subject': subject[:120]}


def list_tickets(customer_id=DEMO_CUSTOMER):
    with connect() as db:
        return rows(db.execute('''SELECT id, customer_id, order_id, subject, description, status
                                  FROM tickets WHERE customer_id=? ORDER BY id DESC''', (customer_id,)))


def get_ticket(ticket_id, customer_id=DEMO_CUSTOMER):
    with connect() as db:
        row = db.execute('''SELECT id, customer_id, order_id, subject, description, status
                            FROM tickets WHERE id=? AND customer_id=?''', (ticket_id, customer_id)).fetchone()
        return dict(row) if row else None


def request_refund(order_id, reason, customer_id=DEMO_CUSTOMER):
    """Create an approval request ONLY. Never transfers money."""
    order = get_order(order_id, customer_id)
    if order is None:
        return {'error': 'Order not found or access denied'}
    if not order['refund_eligible']:
        return {'error': 'Order is not currently marked eligible for a refund'}
    with connect() as db:
        old = db.execute('SELECT id, status FROM refunds WHERE order_id=? AND customer_id=?',
                         (order_id, customer_id)).fetchone()
        if old:
            return {'request_id': old['id'], 'status': old['status'], 'note': 'Existing request; not duplicated'}
        cursor = db.execute('INSERT INTO refunds(customer_id, order_id, reason) VALUES (?,?,?)',
                            (customer_id, order_id, reason[:500]))
        return {'request_id': cursor.lastrowid, 'status': 'PENDING', 'note': 'Manager approval required; no money moved'}


def list_refunds(customer_id=DEMO_CUSTOMER, pending_only=False):
    with connect() as db:
        if pending_only:
            return rows(db.execute('SELECT * FROM refunds WHERE customer_id=? AND status=? ORDER BY id DESC',
                                   (customer_id, 'PENDING')))
        return rows(db.execute('SELECT * FROM refunds WHERE customer_id=? ORDER BY id DESC', (customer_id,)))


def decide_refund(request_id, approve, customer_id=DEMO_CUSTOMER):
    """A HUMAN calls this endpoint; never exposed as an LLM/MCP tool."""
    status = 'APPROVED' if approve else 'REJECTED'
    with connect() as db:
        current = db.execute('SELECT status FROM refunds WHERE id=? AND customer_id=?',
                             (request_id, customer_id)).fetchone()
        if not current:
            return {'error': 'Refund request not found'}
        if current['status'] != 'PENDING':
            return {'error': 'This request has already been decided', 'status': current['status']}
        db.execute('UPDATE refunds SET status=? WHERE id=? AND customer_id=?', (status, request_id, customer_id))
        return {'request_id': request_id, 'status': status, 'note': 'Approval record only; no payment processed'}


def new_conversation(customer_id=DEMO_CUSTOMER):
    chat_id = str(uuid4())
    with connect() as db:
        db.execute('INSERT INTO conversations VALUES (?,?)', (chat_id, customer_id))
    return chat_id


def conversation_exists(chat_id, customer_id=DEMO_CUSTOMER):
    with connect() as db:
        return bool(db.execute('SELECT 1 FROM conversations WHERE id=? AND customer_id=?',
                               (chat_id, customer_id)).fetchone())


def list_conversations(customer_id=DEMO_CUSTOMER):
    with connect() as db:
        return rows(db.execute('SELECT id FROM conversations WHERE customer_id=? ORDER BY rowid DESC',
                               (customer_id,)))


if __name__ == '__main__':
    init_db()
    print('Database ready:', DB_PATH)
    print('Sample orders:', list_orders())
