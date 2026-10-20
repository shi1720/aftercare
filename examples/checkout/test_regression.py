"""Regression tests for tenant-scoped checkout idempotency."""
import unittest
from service import Checkout


class IdempotencyRegression(unittest.TestCase):
    def setUp(self):
        self.checkout = Checkout()

    def test_retry_sequence_returns_original_capture(self):
        first = self.checkout.charge("alice", "order-7", 1500)
        second = self.checkout.charge("alice", "order-7", 1500)
        self.assertIs(first, second)
        self.assertEqual(first["id"], "charge-1")
        self.assertEqual(len(self.checkout.ledger), 1)
        for _ in range(24):
            self.assertIs(first, self.checkout.charge("alice", "order-7", 1500))
        self.assertEqual(len(self.checkout.ledger), 1)

    def test_conflicting_retry_fails_and_keeps_original(self):
        first = self.checkout.charge("alice", "order-7", 1500)
        with self.assertRaises(ValueError):
            self.checkout.charge("alice", "order-7", 1501)
        self.assertEqual(len(self.checkout.ledger), 1)
        self.assertEqual(first["amount"], 1500)
        self.assertIs(first, self.checkout.charge("alice", "order-7", 1500))
        self.assertEqual(len(self.checkout.ledger), 1)

    def test_same_key_is_separate_per_tenant(self):
        alice = self.checkout.charge("alice", "shared", 900)
        bob = self.checkout.charge("bob", "shared", 900)
        self.assertIsNot(alice, bob)
        self.assertNotEqual(alice["id"], bob["id"])
        self.assertEqual(len(self.checkout.ledger), 2)
        self.assertIs(alice, self.checkout.charge("alice", "shared", 900))
        self.assertIs(bob, self.checkout.charge("bob", "shared", 900))
        self.assertEqual(len(self.checkout.ledger), 2)

    def test_tenant_amounts_do_not_conflict(self):
        self.checkout.charge("alice", "shared", 900)
        other = self.checkout.charge("bob", "shared", 901)
        self.assertEqual(other["amount"], 901)
        with self.assertRaises(ValueError):
            self.checkout.charge("bob", "shared", 900)
        self.assertEqual(len(self.checkout.ledger), 2)

    def test_invalid_retry_does_not_touch_ledger(self):
        self.checkout.charge("alice", "order-8", 100)
        with self.assertRaises(ValueError):
            self.checkout.charge("alice", "order-8", True)
        self.assertEqual(len(self.checkout.ledger), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
