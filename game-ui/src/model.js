export const VIEW_SCHEMA_VERSION = "scienceutopia.replay-view.v1";

export function validateReplay(data) {
  if (!data || data.schema_version !== VIEW_SCHEMA_VERSION) {
    throw new Error(`Unsupported replay schema: ${data?.schema_version ?? "missing"}`);
  }
  if (!Array.isArray(data.events) || !Array.isArray(data.frames)) {
    throw new Error("Replay must contain events and frames arrays.");
  }
  if (data.frames.length !== data.events.length + 1) {
    throw new Error("Replay frames must include cursor zero and one frame per event.");
  }
  data.frames.forEach((frame, cursor) => {
    if (frame.cursor !== cursor) throw new Error(`Invalid frame cursor ${frame.cursor}.`);
    if (cursor > 0 && frame.event_id !== data.events[cursor - 1].event_id) {
      throw new Error(`Frame ${cursor} does not match its canonical event.`);
    }
  });
  return data;
}

export function frameAt(data, cursor) {
  const bounded = Math.max(0, Math.min(Number(cursor), data.events.length));
  return {
    cursor: bounded,
    frame: data.frames[bounded],
    event: bounded === 0 ? null : data.events[bounded - 1],
  };
}

export function eventLabel(event) {
  if (!event) return "World ready";
  const labels = {
    "agent.registered": "Researcher arrives",
    "paper.submitted": "Paper submitted",
    "review.completed": "Review completed",
    "paper.decided": "Publication decided",
    "resource.changed": event.payload.delta >= 0 ? "Resources received" : "Research costs paid",
    "resource.balance_reported": "Ledger reconciled",
    "year.completed": "Year completed",
  };
  return labels[event.event_type] ?? event.event_type;
}

export function eventDescription(event) {
  if (!event) return "Press play or step forward to watch this scientific world unfold.";
  const actor = event.actor_ids[0] ?? "the system";
  const paper = event.artifact_ids[0] ?? "";
  switch (event.event_type) {
    case "agent.registered":
      return `${actor} joined ${event.payload.institution ?? "the research commons"}.`;
    case "paper.submitted":
      return `${actor} submitted “${event.payload.title ?? paper}” to ${event.payload.conference ?? "a venue"}.`;
    case "review.completed":
      return `${actor} reviewed ${paper} with score ${event.payload.score ?? "—"}.`;
    case "paper.decided":
      return `${paper} was ${event.payload.decision ?? "decided"}.`;
    case "resource.changed": {
      const delta = Number(event.payload.delta ?? 0);
      return `${actor}'s resources changed by ${delta > 0 ? "+" : ""}${delta} (${String(event.payload.category ?? "change").replaceAll("_", " ")}).`;
    }
    case "resource.balance_reported":
      return `${actor}'s ledger closed at ${event.payload.closing_balance ?? "—"} credits.`;
    case "year.completed":
      return `Year ${event.year} is complete.`;
    default:
      return `${event.event_type} occurred.`;
  }
}

export function agentLocation(event, agentId) {
  if (!event?.actor_ids.includes(agentId)) return "home";
  if (event.event_type.startsWith("paper.") || event.event_type === "review.completed") return "forum";
  if (event.event_type.startsWith("resource.")) return "funding";
  return "home";
}

export function deriveSummary(state) {
  const agents = Object.values(state.agents ?? {});
  const artifacts = Object.values(state.artifacts ?? {});
  return {
    researchers: agents.length,
    activeResearchers: agents.filter((agent) => agent.active).length,
    totalResources: agents.reduce((sum, agent) => sum + Number(agent.balance ?? 0), 0),
    papers: artifacts.length,
    accepted: artifacts.filter((artifact) => artifact.status === "accept").length,
  };
}
