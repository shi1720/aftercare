"""Deliberately faulty first-party sandbox. Credits never represent real money.

Duo must repair the implementation and add a regression test on a repair branch.
This fixture is intentionally kept faulty on main so judges can reproduce it.
"""


class Checkout:
    def __init__(self):
        self.ledger = []
        self.requests = {}

    def charge(self, tenant, key, amount):
        if not tenant or not key or type(amount) is not int or not 0 < amount <= 100000:
            raise ValueError("Invalid sandbox charge")
        identity = (tenant, key)
        # Defect: the retry lookup was removed during a refactor.
        record = {"id": f"charge-{len(self.ledger) + 1}", "tenant": tenant,
                  "key": key, "amount": amount}
        self.ledger.append(record)
        self.requests[identity] = record
        return record

    def health(self):
        return {"status": "healthy"}
