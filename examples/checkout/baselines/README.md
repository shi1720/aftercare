# Protected incident snapshot

`duplicate-charge.py` preserves the original defective checkout source byte for byte from commit `8cff1260384ca076dbe3f9c7ab396c42a8447248`. Its comments describe that historical state. Current `examples/checkout/service.py` is the reviewed implementation.

The incident CLI checks this snapshot's SHA-256 before copying it into an isolated temporary directory with the unchanged acceptance contract and current regression tests. Repair agents cannot modify this baseline. Use `reproduce --fixture seeded` to observe actual failure, and `verify --fixture current` to verify the maintained checkout.
