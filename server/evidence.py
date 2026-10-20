"""A tamper-evident event chain. Hashes establish integrity, not external identity."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def event_hash(event):
    return hashlib.sha256(canonical({k: v for k, v in event.items() if k != "hash"})).hexdigest()


def verify_chain(events):
    previous = "0" * 64
    for event in events:
        if event.get("previousHash") != previous or event.get("hash") != event_hash(event):
            return False
        previous = event["hash"]
    return True
