from dataclasses import dataclass

import pytest

from utopia.agents.base_agent import MultiAgentEcosystem
from utopia.agents.registry import ActorCodecRegistry


@dataclass
class ScientificGuild:
    id: str
    charter: dict
    llm: object = None


def test_new_actor_ontology_is_not_limited_to_legacy_researcher_classes(monkeypatch):
    codecs = ActorCodecRegistry()
    codecs.register("scientific-guild", ScientificGuild,
        dump=lambda a: {"id": a.id, "charter": a.charter},
        load=lambda data, llm: ScientificGuild(**data, llm=llm))
    monkeypatch.setattr("utopia.agents.registry.ACTOR_CODECS", codecs)
    original = MultiAgentEcosystem({})
    original.add_agent(ScientificGuild("guild-1", {"roles": ["replicate", "maintain-commons"], "rules": {"new": [1, 2]}}))
    saved = original.to_dict()
    model = object()
    resumed = MultiAgentEcosystem.from_dict(saved, llm=model)
    actor = resumed.agent_population["guild-1"]
    assert isinstance(actor, ScientificGuild) and actor.llm is model
    assert resumed.to_dict() == saved
    assert actor.charter == original.agent_population["guild-1"].charter


def test_unregistered_codec_cannot_silently_drop_an_actor():
    registry = ActorCodecRegistry()
    with pytest.raises(ValueError, match="unregistered"):
        registry.decode({"actor_codec": "new-kind", "version": 1, "id": "actor-1", "state": {}}, llm=None)


def test_codec_rejects_identity_changes():
    registry = ActorCodecRegistry()
    registry.register("guild", ScientificGuild, dump=lambda a: {},
                      load=lambda data, llm: ScientificGuild("changed", {}, llm))
    with pytest.raises(ValueError, match="identity"):
        registry.decode({"actor_codec": "guild", "version": 1, "id": "original", "state": {}}, llm=None)
