"""Deterministic, prompt-free provenance for the funding application pipeline."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from utopia.utils.data_utils import write_json_atomic


SCHEMA = "scienceutopia.funding_application_trace.v1"


class FundingApplicationTrace:
    """Track conservation of applications across institutional stages.

    Records identifiers and validation outcomes only. Prompts, proposals, model
    messages, and exception strings are deliberately excluded from the audit.
    """

    def __init__(self, year, output_dir):
        self.year = int(year)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.output_dir / f"funding_application_trace_year_{year}.jsonl"
        self.summary_path = self.output_dir / f"funding_application_trace_year_{year}.summary.json"
        self.events_path.write_text("", encoding="utf-8")
        self._sequence = 0
        self._states = {}
        self._reason_counts = Counter()
        self._event_counts = Counter()
        self._generation_outcomes = Counter()

    @staticmethod
    def _identity(metadata):
        agent = metadata.get("agent")
        return getattr(agent, "id", None), metadata.get("program_id")

    def _emit(self, trace_id, event, *, attempt=None, outcome=None, reason=None, **fields):
        state = self._states[trace_id]
        self._sequence += 1
        self._event_counts[event] += 1
        record = {
            "schema": SCHEMA,
            "sequence": self._sequence,
            "year": self.year,
            "trace_id": trace_id,
            "agent_id": state["agent_id"],
            "program_id": state["program_id"],
            "event": event,
        }
        if attempt is not None:
            record["attempt"] = int(attempt)
        if outcome is not None:
            record["outcome"] = outcome
            if event == "generation_attempt":
                self._generation_outcomes[outcome] += 1
        if reason is not None:
            record["reason"] = reason
            self._reason_counts[reason] += 1
        record.update({key: value for key, value in fields.items() if value is not None})
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def target(self, metadata, ordinal):
        trace_id = f"y{self.year}-a{int(ordinal):06d}"
        if trace_id in self._states:
            raise ValueError(f"duplicate funding application trace ID: {trace_id}")
        agent_id, program_id = self._identity(metadata)
        if not isinstance(agent_id, str) or not isinstance(program_id, str):
            raise ValueError("funding application target requires string agent/program IDs")
        metadata["_application_trace_id"] = trace_id
        self._states[trace_id] = {
            "agent_id": agent_id,
            "program_id": program_id,
            "validated": False,
            "submitted": None,
            "dropped": False,
            "evaluation": False,
            "decision": False,
            "funded": False,
            "allocation_recorded": False,
            "allocation_applied": False,
        }
        self._emit(trace_id, "target", outcome="selected")
        return trace_id

    def generation_attempt(self, metadata, attempt, outcome, reason=None):
        self._emit(metadata["_application_trace_id"], "generation_attempt",
                   attempt=attempt, outcome=outcome, reason=reason)

    def validated(self, metadata, proposal, attempt):
        trace_id = metadata["_application_trace_id"]
        state = self._states[trace_id]
        state["validated"] = True
        state["submitted"] = bool(proposal.get("submit", True))
        proposal["_application_trace_id"] = trace_id
        self._emit(trace_id, "validation", attempt=attempt, outcome="valid")
        if not state["submitted"]:
            self._emit(trace_id, "submission", outcome="declined_by_agent",
                       reason="submit_false")

    def dropped(self, metadata, attempt, reason):
        trace_id = metadata["_application_trace_id"]
        self._states[trace_id]["dropped"] = True
        self._emit(trace_id, "submission", attempt=attempt, outcome="dropped", reason=reason)

    def duplicate(self, application):
        trace_id = application.get("_application_trace_id")
        if trace_id not in self._states:
            return
        self._states[trace_id]["dropped"] = True
        self._emit(trace_id, "collection", outcome="dropped",
                   reason="duplicate_agent_program")

    def evaluation(self, application):
        trace_id = application.get("_application_trace_id")
        if trace_id not in self._states:
            return
        self._states[trace_id]["evaluation"] = True
        self._emit(trace_id, "evaluation", outcome="included")

    def decision(self, record):
        trace_id = record.get("application_trace_id")
        if trace_id not in self._states:
            return
        state = self._states[trace_id]
        state["decision"] = True
        state["funded"] = bool(record.get("funded", False))
        self._emit(
            trace_id,
            "decision",
            outcome="funded" if state["funded"] else "not_funded",
            imputed_tail=bool(record.get("imputed_tail", False)),
            fallback_ranking=bool(record.get("fallback_ranking", False)),
        )

    def allocation(self, trace_id, applied):
        if trace_id not in self._states:
            return
        state = self._states[trace_id]
        state["allocation_recorded"] = True
        state["allocation_applied"] = bool(applied)
        self._emit(trace_id, "allocation",
                   outcome="applied" if applied else "not_applied")

    def summary(self):
        states = list(self._states.values())
        failures = []
        for trace_id, state in self._states.items():
            if not state["validated"] and not state["dropped"]:
                failures.append(f"{trace_id}: no terminal generation outcome")
            if (state["validated"] and state["submitted"] and not state["dropped"]
                    and not state["evaluation"]):
                failures.append(f"{trace_id}: submitted but not evaluated")
            if state["evaluation"] and not state["decision"]:
                failures.append(f"{trace_id}: evaluated but no decision")
            if state["funded"] and not state["allocation_recorded"]:
                failures.append(f"{trace_id}: funded but no allocation outcome")

        summary = {
            "schema": SCHEMA,
            "year": self.year,
            "passed": not failures,
            "failures": failures,
            "counts": {
                "targets": len(states),
                "validated": sum(state["validated"] for state in states),
                "submitted": sum(state["submitted"] is True for state in states),
                "declined_by_agent": sum(state["submitted"] is False for state in states),
                "dropped": sum(state["dropped"] for state in states),
                "evaluated": sum(state["evaluation"] for state in states),
                "decided": sum(state["decision"] for state in states),
                "funded": sum(state["funded"] for state in states),
                "allocations_recorded": sum(state["allocation_recorded"] for state in states),
                "allocations_applied": sum(state["allocation_applied"] for state in states),
                "generation_attempts": self._event_counts["generation_attempt"],
                "semantic_invalid_attempts": self._generation_outcomes["invalid"],
                "request_error_attempts": self._generation_outcomes["request_error"],
            },
            "reason_counts": dict(sorted(self._reason_counts.items())),
            "events_path": self.events_path.name,
        }
        write_json_atomic(self.summary_path, summary, indent=2)
        return summary
