"""Explicit, versioned codecs for actor kinds beyond the legacy roster.

Registration is trusted application code, never a class import path supplied
by a model. Unknown actors fail instead of silently disappearing on save.
"""
from __future__ import annotations

import json
from typing import Callable


class ActorCodecRegistry:
    def __init__(self):
        self._encoders = {}
        self._decoders = {}

    def register(self, codec_id: str, actor_type: type, *, dump: Callable,
                 load: Callable, version: int = 1):
        if (not isinstance(codec_id, str) or not codec_id or not isinstance(actor_type, type)
                or type(version) is not int or version < 1 or not callable(dump) or not callable(load)):
            raise ValueError("actor codec requires id, class, version and dump/load callables")
        key = (codec_id, version)
        if actor_type in self._encoders or key in self._decoders:
            raise ValueError("actor codec is already registered")
        self._encoders[actor_type] = (codec_id, version, dump)
        self._decoders[key] = load

    def encode(self, actor):
        entry = self._encoders.get(type(actor))
        if entry is None:
            return None
        codec_id, version, dump = entry
        record = {"actor_codec": codec_id, "version": version, "id": actor.id,
                  "state": dump(actor)}
        return json.loads(json.dumps(record, allow_nan=False))

    def decode(self, record, *, llm):
        if set(record) != {"actor_codec", "version", "id", "state"}:
            raise ValueError("invalid actor codec envelope")
        key = (record["actor_codec"], record["version"])
        if key not in self._decoders:
            raise ValueError(f"unregistered actor codec {key!r}; install the same trusted plugin")
        json.dumps(record, allow_nan=False)
        actor = self._decoders[key](record["state"], llm=llm)
        if actor.id != record["id"]:
            raise ValueError("restored actor identity changed")
        return actor


ACTOR_CODECS = ActorCodecRegistry()
