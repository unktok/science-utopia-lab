import json
from types import SimpleNamespace

from utopia.agents.funding_agents import FundingAgency
from utopia.agents.researcher_agents import UniversityResearcher
from utopia.funding.application_trace import FundingApplicationTrace
from utopia.runtime.checkpointing import simulation_replay_paths
from utopia.simulation import Simulation


def metadata(agent_id, program_id):
    return {"agent": SimpleNamespace(id=agent_id), "program_id": program_id}


def test_complete_trace_conserves_targets_without_recording_content(tmp_path):
    trace = FundingApplicationTrace(1, tmp_path)
    first = metadata("researcher-1", "program-a")
    second = metadata("researcher-2", "program-b")
    trace.target(first, 1)
    trace.target(second, 2)

    trace.generation_attempt(first, 1, "invalid", "proposal is None")
    proposal = {"submit": True, "research_proposal": "SECRET", "relevant_projects": []}
    trace.generation_attempt(first, 2, "valid")
    trace.validated(first, proposal, 2)
    trace.evaluation(proposal)
    trace.decision({"application_trace_id": proposal["_application_trace_id"], "funded": True})
    trace.allocation(proposal["_application_trace_id"], True)

    declined = {"submit": False, "research_proposal": "OTHER SECRET",
                "relevant_projects": []}
    trace.generation_attempt(second, 1, "valid")
    trace.validated(second, declined, 1)

    summary = trace.summary()
    assert summary["passed"] is True
    assert summary["counts"] == {
        "targets": 2,
        "validated": 2,
        "submitted": 1,
        "declined_by_agent": 1,
        "dropped": 0,
        "evaluated": 1,
        "decided": 1,
        "funded": 1,
        "allocations_recorded": 1,
        "allocations_applied": 1,
        "generation_attempts": 3,
        "semantic_invalid_attempts": 1,
        "sanitized_reference_attempts": 0,
        "request_error_attempts": 0,
    }
    audit = trace.events_path.read_text()
    assert "SECRET" not in audit
    assert [json.loads(line)["sequence"] for line in audit.splitlines()] == list(range(1, 12))


def test_terminal_drop_is_explained_but_missing_evaluation_is_not(tmp_path):
    trace = FundingApplicationTrace(2, tmp_path)
    dropped = metadata("researcher-1", "program-a")
    missing = metadata("researcher-2", "program-b")
    trace.target(dropped, 1)
    trace.target(missing, 2)
    trace.generation_attempt(dropped, 1, "invalid", "missing 'submit' field")
    trace.dropped(dropped, 5, "missing 'submit' field")
    submitted = {"submit": True}
    trace.generation_attempt(missing, 1, "valid")
    trace.validated(missing, submitted, 1)

    summary = trace.summary()
    assert summary["passed"] is False
    assert summary["counts"]["dropped"] == 1
    assert summary["failures"] == ["y2-a000002: submitted but not evaluated"]


def test_normalized_rankings_preserve_application_trace_identity():
    apps = [
        {"applicant_id": "r1", "_application_trace_id": "y1-a000001"},
        {"applicant_id": "r2", "_application_trace_id": "y1-a000002"},
    ]
    normalized, rejects = FundingAgency.normalize_ranked_applications(
        [{"application_id": 0, "applicant_id": "r1", "rank": 1}], apps)
    assert rejects == []
    assert {row["application_trace_id"] for row in normalized} == {
        "y1-a000001", "y1-a000002"
    }
    assert normalized[1]["imputed_tail"] is True


def test_portable_replay_owns_trace_outputs(tmp_path):
    paths = simulation_replay_paths(tmp_path / "out", tmp_path / "docs", 1)
    assert "output/funding_application_trace_year_1.jsonl" in paths
    assert "output/funding_application_trace_year_1.summary.json" in paths


class BatchModel:
    def __init__(self, batches):
        self.batches = list(batches)

    def generate_batch(self, prompts, **_kwargs):
        proposals = self.batches.pop(0)
        assert len(proposals) == len(prompts)
        return [(proposal, []) for proposal in proposals]


class Applicant:
    def __init__(self, agent_id):
        self.id = agent_id

    def funding_application_prompt(self, program, **_kwargs):
        return "prompt", {}, {
            "agent": self,
            "program_id": program,
            "all_papers": [{"id": "paper-1", "status": "accept"}],
        }


def test_zero_paper_prompt_has_empty_valid_example():
    researcher = SimpleNamespace(
        generate_research_proposal=True,
        expertise=[SimpleNamespace(topic="machine_learning")],
        university_name="Fixture University",
        resources=50,
    )
    program = SimpleNamespace(
        program_id="program-a", name="Program A",
        research_directions=[SimpleNamespace(topic="machine_learning")],
    )

    prompt, _, metadata_row = UniversityResearcher.funding_application_prompt(
        researcher, program, [], []
    )

    assert '"relevant_projects": []' in prompt
    assert "No past papers are listed" in prompt
    assert "between 0 and -1" not in prompt
    assert "[0, 2, 1]" not in prompt
    assert metadata_row["all_papers"] == []


def test_funding_prompt_example_never_exceeds_available_papers():
    researcher = SimpleNamespace(
        generate_research_proposal=True,
        expertise=[SimpleNamespace(topic="machine_learning")],
        university_name="Fixture University",
        resources=50,
    )
    program = SimpleNamespace(
        program_id="program-a", name="Program A",
        research_directions=[SimpleNamespace(topic="machine_learning")],
    )
    papers = [
        {"id": f"paper-{index}", "status": "accept", "title": "T", "abstract": "A"}
        for index in range(2)
    ]

    prompt, _, _ = UniversityResearcher.funding_application_prompt(
        researcher, program, papers, []
    )

    assert '"relevant_projects": [0, 1]' in prompt
    assert "between 0 and 1" in prompt
    assert "[0, 2, 1]" not in prompt


def batch_simulation(tmp_path, batches):
    simulation = Simulation.__new__(Simulation)
    simulation.llm = BatchModel(batches)
    simulation._funding_application_traces = {1: FundingApplicationTrace(1, tmp_path)}
    simulation.conference_system = SimpleNamespace(
        authors_to_accepted_papers={}, authors_to_rejected_papers={})
    return simulation


def test_batch_generation_keeps_trace_identity_across_semantic_retry(tmp_path):
    invalid = {"submit": True, "research_proposal": "x", "relevant_projects": [99]}
    valid = {"submit": True, "research_proposal": "x", "relevant_projects": [0]}
    simulation = batch_simulation(tmp_path, [[invalid], [valid]])
    agent = Applicant("researcher-1")
    metadata_row = {
        "agent": agent, "program_id": "program-a",
        "all_papers": [{"id": "paper-1", "status": "accept"}],
    }
    trace = simulation._funding_application_traces[1]
    trace.target(metadata_row, 1)

    results = simulation._generate_funding_applications_batch(
        1, {"program-a": "program-a"}, ["prompt"], [metadata_row], {})

    assert len(results) == 1
    assert results[0][2]["_application_trace_id"] == "y1-a000001"
    summary = trace.summary()
    assert summary["counts"]["generation_attempts"] == 2
    assert summary["counts"]["semantic_invalid_attempts"] == 1


def test_batch_generation_records_terminal_semantic_drop(tmp_path):
    invalid = {"submit": True, "research_proposal": "x", "relevant_projects": [99]}
    simulation = batch_simulation(tmp_path, [[dict(invalid)] for _ in range(5)])
    agent = Applicant("researcher-1")
    metadata_row = {
        "agent": agent, "program_id": "program-a",
        "all_papers": [{"id": "paper-1", "status": "accept"}],
    }
    trace = simulation._funding_application_traces[1]
    trace.target(metadata_row, 1)

    results = simulation._generate_funding_applications_batch(
        1, {"program-a": "program-a"}, ["prompt"], [metadata_row], {})

    assert results == []
    summary = trace.summary()
    assert summary["passed"] is True
    assert summary["counts"]["dropped"] == 1
    assert summary["counts"]["generation_attempts"] == 5


def test_zero_paper_invalid_references_are_sanitized_without_retry(tmp_path):
    proposal = {"submit": True, "research_proposal": "x", "relevant_projects": [0, 2, 1]}
    simulation = batch_simulation(tmp_path, [[proposal]])
    agent = Applicant("researcher-1")
    metadata_row = {"agent": agent, "program_id": "program-a", "all_papers": []}
    trace = simulation._funding_application_traces[1]
    trace.target(metadata_row, 1)

    results = simulation._generate_funding_applications_batch(
        1, {"program-a": "program-a"}, ["prompt"], [metadata_row], {}
    )

    assert len(results) == 1
    assert results[0][2]["relevant_projects"] == []
    summary = trace.summary()
    assert summary["counts"]["generation_attempts"] == 1
    assert summary["counts"]["semantic_invalid_attempts"] == 0
    assert summary["counts"]["sanitized_reference_attempts"] == 1
    assert summary["counts"]["dropped"] == 0
    assert summary["reason_counts"] == {"invalid_paper_indices_removed": 1}
