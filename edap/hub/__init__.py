"""The hub link (plan 0015): one websocket a peer keeps open to its hub.

`protocol` holds the frames both ends share, `outbox` the peer's persistent queue, `peer` the
peer's side of the link and `nodes` the hub's side and its node registry.
"""
