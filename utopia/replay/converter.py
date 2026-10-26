"""Convert saved ScienceUtopia artifacts to a deterministic event stream.

This module is a sidecar: it reads checkpoint exports and never imports or
executes the simulator or an LLM backend.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

from .events import EventEnvelope, canonical_event_stream_hash, validate_references


@dataclass(frozen=True)
class ArtifactBundle:
    checkpoint: Path
    resource_ledger: Path | None = None
    resource_balances: Path | None = None

    @classmethod
    def discover(cls, checkpoint: str | Path) -> "ArtifactBundle":
        checkpoint_path = Path(checkpoint)
        parent = checkpoint_path.parent
        ledger = parent / "resource_ledger.jsonl"
        balances = parent / "resource_balances.jsonl"
        return cls(
            checkpoint=checkpoint_path,
            resource_ledger=ledger if ledger.exists() else None,
            resource_balances=balances if balances.exists() else None,
        )


def _read_json(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_number}: expected a JSON object")
                rows.append(value)
    return rows


def _paper_rows(checkpoint: Mapping[str, Any]) -> list[dict[str, Any]]:
    papers = checkpoint.get("paper_tracker", {}).get("papers", [])
    if isinstance(papers, Mapping):
        papers = list(papers.values())
    return sorted(papers, key=lambda paper: (int(paper.get("year", 0)), str(paper["id"])))


def _paper_rounds(paper: Mapping[str, Any]) -> list[dict[str, Any]]:
    rounds = paper.get("review_history") or []
    if rounds:
        return sorted(
            rounds,
            key=lambda row: (
                int(row.get("year", paper.get("year", 0))),
                str(row.get("conference", "")),
            ),
        )
    return [{
        "year": paper.get("year", 0),
        "conference": paper.get("conference"),
        "reviews": paper.get("reviews", []),
        "decision": paper.get("status"),
    }]


def _spec(
    *,
    year: int,
    phase: int,
    event_type: str,
    stable_order: tuple[Any, ...],
    actor_ids: Iterable[str] = (),
    artifact_ids: Iterable[str] = (),
    payload: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "year": int(year),
        "phase": int(phase),
        "event_type": event_type,
        "stable_order": stable_order,
        "actor_ids": tuple(actor_ids),
        "artifact_ids": tuple(artifact_ids),
        "payload": dict(payload or {}),
        "provenance": dict(provenance or {}),
    }


def convert_artifacts(bundle: ArtifactBundle) -> list[EventEnvelope]:
    """Convert a saved checkpoint bundle without invoking simulation code."""

    checkpoint = _read_json(bundle.checkpoint)
    ledger = _read_jsonl(bundle.resource_ledger)
    balances = _read_jsonl(bundle.resource_balances)
    specs: list[dict[str, Any]] = []

    first_balances: dict[str, Mapping[str, Any]] = {}
    for row in sorted(
        balances, key=lambda item: (int(item["year"]), str(item["researcher_id"]))
    ):
        first_balances.setdefault(str(row["researcher_id"]), row)

    agents = checkpoint.get("ecosystem_data", {}).get("agents", [])
    for source_index, agent in enumerate(sorted(agents, key=lambda row: str(row["id"]))):
        actor_id = str(agent["id"])
        balance = first_balances.get(actor_id)
        initial_balance = balance.get("opening_balance") if balance else agent.get("resources")
        specs.append(_spec(
            year=0,
            phase=0,
            event_type="agent.registered",
            stable_order=(actor_id,),
            actor_ids=(actor_id,),
            payload={
                "agent_type": agent.get("type"),
                "institution": agent.get("university_name") or agent.get("company_name"),
                "initial_balance": initial_balance,
                "initial_active": (
                    balance.get("opening_active", True)
                    if balance
                    else agent.get("is_active", True)
                ),
            },
            provenance={"source": "checkpoint.ecosystem_data.agents", "record": source_index},
        ))

    for paper_index, paper in enumerate(_paper_rows(checkpoint)):
        paper_id = str(paper["id"])
        author_id = str(paper["author_id"])
        for round_index, round_row in enumerate(_paper_rounds(paper)):
            year = int(round_row.get("year", paper.get("year", 0)))
            round_key = (year, paper_id, round_index)
            specs.append(_spec(
                year=year,
                phase=2,
                event_type="paper.submitted",
                stable_order=round_key,
                actor_ids=(author_id,),
                artifact_ids=(paper_id,),
                payload={
                    "title": paper.get("title"),
                    "conference": round_row.get("conference") or paper.get("conference"),
                    "topics": paper.get("topics", []),
                    "submission_round": round_index,
                },
                provenance={
                    "source": "checkpoint.paper_tracker.papers",
                    "record": paper_index,
                    "round": round_index,
                },
            ))
            reviews = round_row.get("reviews") or []
            for review_index, review in enumerate(reviews):
                reviewer_id = str(review["reviewer_id"])
                specs.append(_spec(
                    year=year,
                    phase=3,
                    event_type="review.completed",
                    stable_order=round_key + (reviewer_id, review_index),
                    actor_ids=(reviewer_id,),
                    artifact_ids=(paper_id,),
                    payload={
                        "conference": (
                            review.get("conference_id") or round_row.get("conference")
                        ),
                        "score": review.get("overall_score"),
                        "justification": review.get("justification"),
                        "submission_round": round_index,
                    },
                    provenance={
                        "source": (
                            "checkpoint.paper_tracker.papers.review_history.reviews"
                        ),
                        "record": paper_index,
                        "round": round_index,
                        "review": review_index,
                    },
                ))
            decision = round_row.get("decision")
            if decision is not None:
                specs.append(_spec(
                    year=year,
                    phase=4,
                    event_type="paper.decided",
                    stable_order=round_key,
                    actor_ids=(author_id,),
                    artifact_ids=(paper_id,),
                    payload={
                        "decision": decision,
                        "score": round_row.get("score"),
                        "conference": (
                            round_row.get("conference") or paper.get("conference")
                        ),
                        "submission_round": round_index,
                    },
                    provenance={
                        "source": "checkpoint.paper_tracker.papers.review_history",
                        "record": paper_index,
                        "round": round_index,
                    },
                ))

    resource_phase = {
        "production_submission_cost": 2,
        "annual_research_cost": 2,
        "resubmission_cost": 2,
        "funding_application_cost": 5,
        "grant_income": 5,
        "industry_income": 5,
    }
    for source_index, row in enumerate(ledger):
        researcher_id = str(row["researcher_id"])
        year = int(row["year"])
        category = str(row.get("category", "resource_change"))
        specs.append(_spec(
            year=year,
            phase=resource_phase.get(category, 5),
            event_type="resource.changed",
            stable_order=(source_index,),
            actor_ids=(researcher_id,),
            artifact_ids=((str(row["paper_id"]),) if row.get("paper_id") else ()),
            payload={
                "category": category,
                "delta": row.get("delta"),
                "requested_delta": row.get("requested_delta"),
                "balance_before": row.get("balance_before"),
                "balance_after": row.get("balance_after"),
                "active_after": row.get("active_after"),
                "uncollected_cost": row.get("uncollected_cost", 0),
            },
            provenance={
                "source": "resource_ledger.jsonl",
                "record": source_index,
                "source_event_id": row.get("event_id"),
            },
        ))

    years: set[int] = set()
    for source_index, row in enumerate(balances):
        researcher_id = str(row["researcher_id"])
        year = int(row["year"])
        years.add(year)
        specs.append(_spec(
            year=year,
            phase=6,
            event_type="resource.balance_reported",
            stable_order=(researcher_id,),
            actor_ids=(researcher_id,),
            payload={
                "opening_balance": row.get("opening_balance"),
                "closing_balance": row.get("closing_balance"),
                "opening_active": row.get("opening_active"),
                "closing_active": row.get("closing_active"),
                "residual": row.get("residual"),
            },
            provenance={"source": "resource_balances.jsonl", "record": source_index},
        ))

    years.update(
        int(row.get("year", 0)) for row in checkpoint.get("yearly_results", [])
    )
    for year in years:
        specs.append(_spec(
            year=year,
            phase=7,
            event_type="year.completed",
            stable_order=(year,),
            payload={"year": year},
            provenance={"source": "checkpoint.yearly_results", "record": year},
        ))

    specs.sort(key=lambda item: (
        item["year"],
        item["phase"],
        item["event_type"],
        item["stable_order"],
    ))
    events = [
        EventEnvelope.create(
            sequence=sequence,
            year=spec["year"],
            phase=spec["phase"],
            event_type=spec["event_type"],
            actor_ids=spec["actor_ids"],
            artifact_ids=spec["artifact_ids"],
            payload=spec["payload"],
            provenance=spec["provenance"],
        )
        for sequence, spec in enumerate(specs)
    ]
    errors = validate_references(events)
    if errors:
        raise ValueError("Invalid canonical event references: " + "; ".join(errors))
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    events = convert_artifacts(ArtifactBundle.discover(args.checkpoint))
    text = "\n".join(
        json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        for event in events
    ) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    print(
        json.dumps({
            "events": len(events),
            "stream_hash": canonical_event_stream_hash(events),
        }),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
