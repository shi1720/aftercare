"""Fixed, first-party fixtures. No user-supplied Python or shell commands execute."""
SAFE_SOURCE = '''"""Synthetic payment service. All amounts are test credits, never money."""
class PaymentService:
    def __init__(self):
        self.ledger = []
        self.requests = {}
        self.orders = {"order-alice": {"tenant": "alice", "amount": 4200}}

    def charge(self, tenant, key, amount):
        if not tenant or not key or not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or amount > 100000:
            raise ValueError("Invalid synthetic charge")
        identity = (tenant, key)
        if identity in self.requests:
            record = self.requests[identity]
            if record["amount"] != amount:
                raise ValueError("Idempotency key conflict")
            return record
        record = {"id": "charge-" + str(len(self.ledger) + 1), "tenant": tenant, "key": key, "amount": amount}
        self.ledger.append(record)
        self.requests[identity] = record
        return record

    def order(self, tenant, order_id):
        record = self.orders.get(order_id)
        if record is None or record["tenant"] != tenant:
            return None
        return record
'''
DUPLICATE_SOURCE = SAFE_SOURCE.replace('        if identity in self.requests:', '        if False and identity in self.requests:')
TENANT_SOURCE = SAFE_SOURCE.replace('if record is None or record["tenant"] != tenant:', 'if record is None:')
UNSAFE_SOURCE = SAFE_SOURCE + '\nimport os\ndef bypass(value):\n    return eval(value)\n'

TEST_RUNNER = r'''
import importlib.util
import json
import sys
import unittest
spec = importlib.util.spec_from_file_location("payment_fixture", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class Contracts(unittest.TestCase):
    def setUp(self):
        self.service = module.PaymentService()
    def test_retry_is_one_charge(self):
        first = self.service.charge("alice", "checkout-1", 4200)
        for _ in range(20):
            self.assertEqual(first, self.service.charge("alice", "checkout-1", 4200))
        self.assertEqual(len(self.service.ledger), 1)
    def test_cross_tenant_order_hidden(self):
        self.assertIsNone(self.service.order("bob", "order-alice"))
    def test_owner_can_read_order(self):
        self.assertEqual(self.service.order("alice", "order-alice")["amount"], 4200)
    def test_keys_are_scoped_to_tenant(self):
        self.service.charge("alice", "shared-key", 4200)
        self.service.charge("bob", "shared-key", 4200)
        self.assertEqual(len(self.service.ledger), 2)
    def test_idempotency_conflict_fails_closed(self):
        self.service.charge("alice", "same-key", 4200)
        with self.assertRaises(ValueError):
            self.service.charge("alice", "same-key", 4201)
        self.assertEqual(len(self.service.ledger), 1)
    def test_invalid_amount_rejected(self):
        for amount in [-1, 0, "4200", True, 100001]:
            with self.assertRaises(ValueError):
                self.service.charge("alice", "invalid", amount)
    def test_missing_order_hidden(self):
        self.assertIsNone(self.service.order("alice", "unknown"))
result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
print(json.dumps({"total": result.testsRun, "passed": result.testsRun-len(result.failures)-len(result.errors), "failures": [case.id().split(".")[-1] for case, _ in result.failures + result.errors]}))
sys.exit(0 if result.wasSuccessful() else 1)
'''

CANARY_RUNNER = r'''
import importlib.util
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
spec = importlib.util.spec_from_file_location("payment_fixture", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
service = module.PaymentService()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        try:
            result = service.charge(body["tenant"], body["key"], body["amount"])
            status = 200
        except ValueError as exc:
            result, status = {"error": str(exc)}, 409
        payload = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        if self.path == "/health":
            payload = b'{"status":"healthy"}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        result = service.order(self.headers.get("X-Tenant"), "order-alice")
        payload = json.dumps(result or {"error": "Not found"}).encode()
        self.send_response(200 if result else 404)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
server = HTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = "http://127.0.0.1:" + str(server.server_port)
with urllib.request.urlopen(url + "/health", timeout=3) as response:
    health = {"httpStatus": response.status, "body": json.load(response)}
responses = []
for index in range(24):
    payload = json.dumps({"tenant": "alice", "key": "checkout-canary", "amount": 4200}).encode()
    req = urllib.request.Request(url + "/charge", payload, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        responses.append(json.load(response)["id"])
leaks = 0
for index in range(8):
    req = urllib.request.Request(url + "/orders/order-alice", headers={"X-Tenant": "bob"})
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            leaks += 1
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
samples = []
observation_seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 0
observation_start = time.monotonic()
while time.monotonic() - observation_start < observation_seconds:
    sample_start = time.monotonic()
    with urllib.request.urlopen(url + "/health", timeout=3) as response:
        healthy = response.status == 200 and json.load(response)["status"] == "healthy"
    payload = json.dumps({"tenant": "alice", "key": "checkout-canary", "amount": 4200}).encode()
    with urllib.request.urlopen(urllib.request.Request(url + "/charge", payload, {"Content-Type": "application/json"}), timeout=3) as response:
        record = json.load(response)
    tenant_hidden = False
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "/orders/order-alice", headers={"X-Tenant": "bob"}), timeout=3) as response:
            pass
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        tenant_hidden = True
    samples.append({"elapsedMs": round((time.monotonic()-observation_start)*1000), "healthPassed": healthy, "idempotencyPassed": record["id"] == responses[0] and len(service.ledger) == 1, "tenantBoundaryPassed": tenant_hidden})
    # The observation interval is a real stability gate, not presentation pacing.
    remaining = min(0.5 - (time.monotonic()-sample_start), observation_seconds-(time.monotonic()-observation_start))
    if remaining > 0:
        time.sleep(remaining)
server.shutdown()
server.server_close()
print(json.dumps({"requests": 32 + len(samples)*2, "canaryRequests": 32, "stabilityRequests": len(samples)*2, "observationMs": round((time.monotonic()-observation_start)*1000) if observation_seconds else 0, "stabilitySamples": samples, "healthProbeRequests": 1 + len(samples), "health": health, "chargeRequests": 24, "uniqueCharges": len(service.ledger), "duplicateCharges": max(0, len(service.ledger)-1), "tenantLeaks": leaks, "ledger": service.ledger, "passed": len(service.ledger)==1 and leaks==0 and all(sample["healthPassed"] and sample["idempotencyPassed"] and sample["tenantBoundaryPassed"] for sample in samples)}))
'''
