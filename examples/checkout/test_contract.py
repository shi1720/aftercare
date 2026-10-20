"""Fixed acceptance contract. Repair workflows must not weaken this file."""
import unittest
from service import Checkout


class CheckoutContract(unittest.TestCase):
    def setUp(self):
        self.checkout = Checkout()

    def test_health_stays_green(self):
        self.assertEqual(self.checkout.health(), {"status": "healthy"})

    def test_retry_captures_once(self):
        first = self.checkout.charge("alice", "order-1", 4200)
        for _ in range(20):
            self.assertEqual(first, self.checkout.charge("alice", "order-1", 4200))
        self.assertEqual(len(self.checkout.ledger), 1)

    def test_key_conflict_rejected(self):
        self.checkout.charge("alice", "order-1", 4200)
        with self.assertRaises(ValueError):
            self.checkout.charge("alice", "order-1", 4201)
        self.assertEqual(len(self.checkout.ledger), 1)

    def test_tenants_have_independent_keys(self):
        self.checkout.charge("alice", "same", 42)
        self.checkout.charge("bob", "same", 42)
        self.assertEqual(len(self.checkout.ledger), 2)

    def test_invalid_amounts(self):
        for amount in [0, -1, True, "4200", 100001]:
            with self.assertRaises(ValueError):
                self.checkout.charge("alice", "invalid", amount)


if __name__ == "__main__":
    unittest.main(verbosity=2)
