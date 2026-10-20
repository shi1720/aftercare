"""First-party sandbox checkout. Credits never represent real money.

Charges are idempotent per (tenant, key): a retry with the same amount returns
the original capture, and a retry with a different amount raises ValueError.
"""


class Checkout:
    def __init__(self):
        self.ledger = []
        self.requests = {}

    def charge(self, tenant, key, amount):
        if not tenant or not key or type(amount) is not int or not 0 < amount <= 100000:
            raise ValueError("Invalid sandbox charge")
        identity = (tenant, key)
        existing = self.requests.get(identity)
        if existing is not None:
            if existing["amount"] != amount:
                raise ValueError("Idempotency key reused with a different amount")
            return existing
        record = {"id": f"charge-{len(self.ledger) + 1}", "tenant": tenant,
                  "key": key, "amount": amount}
        self.ledger.append(record)
        self.requests[identity] = record
        return record

    def health(self):
        return {"status": "healthy"}
