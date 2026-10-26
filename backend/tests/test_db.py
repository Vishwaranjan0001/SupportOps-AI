"""Offline tests: python -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path
import db
from rag import simple_search


class TestSupportOps(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_data, self.previous_db = db.DATA, db.DB_PATH
        db.DATA = Path(self.temp.name)
        db.DB_PATH = db.DATA / 'test.db'
        db.init_db()

    def tearDown(self):
        db.DATA, db.DB_PATH = self.previous_data, self.previous_db
        self.temp.cleanup()

    def test_seed_orders(self):
        self.assertEqual(len(db.list_orders()), 3)

    def test_order_status(self):
        self.assertEqual(db.get_order('ORD-1001')['status'], 'SHIPPED')

    def test_other_customer_denied(self):
        self.assertIsNone(db.get_order('ORD-1002'))

    def test_sql_injection_is_just_data(self):
        self.assertIsNone(db.get_order("ORD-1001' OR 1=1 --"))

    def test_refund_request_needs_eligibility(self):
        self.assertIn('error', db.request_refund('ORD-1001', 'Changed my mind'))

    def test_refund_starts_pending(self):
        result = db.request_refund('ORD-1003', 'Changed my mind')
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(db.list_refunds()[0]['status'], 'PENDING')

    def test_refund_cannot_be_duplicated(self):
        first = db.request_refund('ORD-1003', 'Reason A')
        second = db.request_refund('ORD-1003', 'Reason B')
        self.assertEqual(first['request_id'], second['request_id'])
        self.assertEqual(len(db.list_refunds()), 1)

    def test_manager_approval(self):
        req = db.request_refund('ORD-1003', 'Damaged')
        result = db.decide_refund(req['request_id'], True)
        self.assertEqual(result['status'], 'APPROVED')
        self.assertEqual(db.list_refunds()[0]['status'], 'APPROVED')
        self.assertIn('error', db.decide_refund(req['request_id'], False))

    def test_manager_rejection(self):
        req = db.request_refund('ORD-1003', 'Damaged')
        result = db.decide_refund(req['request_id'], False)
        self.assertEqual(result['status'], 'REJECTED')

    def test_create_ticket(self):
        result = db.create_ticket('ORD-1001', 'Late delivery', 'Please investigate')
        self.assertEqual(result['ticket_id'], 1)
        self.assertEqual(len(db.list_tickets()), 1)

    def test_create_ticket_access(self):
        self.assertIn('error', db.create_ticket('ORD-1002', 'Wrong account', 'Cannot access'))

    def test_conversation_tracking(self):
        chat = db.new_conversation()
        self.assertTrue(db.conversation_exists(chat))
        self.assertFalse(db.conversation_exists(chat, 'cust-002'))

    def test_rag_retrieval(self):
        self.assertEqual(simple_search('What is your refund policy?')[0]['source'], 'refund_policy.txt')

    def test_rag_warranty(self):
        self.assertEqual(simple_search('What warranty do electronics have?')[0]['source'], 'warranty_policy.txt')


if __name__ == '__main__':
    unittest.main()
