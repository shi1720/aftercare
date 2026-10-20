"""A tamper-evident event chain. Hashes establish integrity, not external identity."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def event_hash(event):
    return hashlib.sha256(canonical({k: v for k, v in event.items() if k != "hash"})).hexdigest()


def verify_chain(events):
    if not isinstance(events, list):
        return False
    previous = "0" * 64
    try:
        for event in events:
            if not isinstance(event, dict) or event.get("previousHash") != previous or event.get("hash") != event_hash(event):
                return False
            previous = event["hash"]
        return True
    except (TypeError, ValueError):
        return False
