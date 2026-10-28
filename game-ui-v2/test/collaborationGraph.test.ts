import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildCollaborationEvidenceGraph, graphAtCursor } from "../src/collaborationGraph";
import { parseReplayV2 } from "../src/replay";

const campaignUrl = new URL("../public/data/completed-campaign.replay.json", import.meta.url);
const syntheticUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const pageUrl = new URL("../index.html", import.meta.url);
const load = async (url = campaignUrl) => parseReplayV2(JSON.parse(await readFile(fileURLToPath(url), "utf8")));

describe("verified collaboration evidence graph", () => {
  it("keeps canonical relationship types separate and reports absence explicitly", async () => {
    const graph = buildCollaborationEvidenceGraph(await load());
    const count = (kind: string) => graph.edges.filter((edge) => edge.kind === kind).length;
    expect(graph.truth_status).toBe("verified_replay");
    expect(graph.observation_scope).toBe("loaded_verified_run");
    expect(graph.nodes.filter((node) => node.kind === "researcher")).toHaveLength(12);
    expect(graph.nodes.filter((node) => node.kind === "artifact")).toHaveLength(2);
    expect(graph.nodes.filter((node) => node.kind === "institution")).toHaveLength(2);
    expect(graph.nodes.filter((node) => node.kind === "event")).toHaveLength(28);
    expect({
      affiliation: count("affiliation"), authorship: count("authorship"), coauthor: count("coauthor"),
      reviewer: count("reviewer"), funding_activity: count("funding_activity"), funder: count("funder"), citation: count("citation"),
    }).toEqual({ affiliation: 10, authorship: 2, coauthor: 0, reviewer: 4, funding_activity: 28, funder: 0, citation: 0 });
    expect(graph.observations).toEqual([
      expect.objectContaining({ kind: "coauthor", count: 0, status: "not_observed" }),
      expect.objectContaining({ kind: "reviewer", count: 4, status: "observed" }),
      expect.objectContaining({ kind: "funder", count: 0, status: "identity_missing" }),
      expect.objectContaining({ kind: "citation", count: 0, status: "not_observed" }),
    ]);
  });

  it("does not turn anonymous review or funding activity into guessed identity edges", async () => {
    const replay = await load();
    const firstReview = replay.canonical.events.find((event) => event.kind === "review.completed")!;
    firstReview.actor_ids = [];
    const graph = buildCollaborationEvidenceGraph(replay);
    expect(graph.edges.filter((edge) => edge.kind === "reviewer")).toHaveLength(3);
    expect(graph.edges.filter((edge) => edge.kind === "funder")).toHaveLength(0);
    expect(graph.edges.filter((edge) => edge.kind === "funding_activity")).toHaveLength(28);
  });

  it("bounds graph evidence and lineage by the canonical replay cursor", async () => {
    const graph = graphAtCursor(buildCollaborationEvidenceGraph(await load()), 20_200);
    expect(graph.lineage.every((event) => event.logical_timestamp_ms <= 20_200)).toBe(true);
    expect(graph.edges.every((edge) => graph.lineage.some((event) => event.id === edge.event_id))).toBe(true);
    expect(graph.edges.filter((edge) => edge.kind === "reviewer")).toHaveLength(2);
  });

  it("types every visual graph decision as presentation-only and ignores choreography", async () => {
    const replay = await load();
    const summarize = () => {
      const graph = buildCollaborationEvidenceGraph(replay);
      return { nodes: graph.nodes, edges: graph.edges, observations: graph.observations, presentation: graph.presentation };
    };
    const baseline = summarize();
    replay.choreography.actions = [];
    replay.choreography.flows = [];
    replay.choreography.epistemic_flows = [];
    replay.choreography.interior_activities = [];
    replay.ambient.actors = [];
    replay.ambient.effects = [];
    expect(summarize()).toEqual(baseline);
    expect(baseline.presentation).toEqual({
      truth_status: "presentation_only",
      fields: ["force_layout", "node_placement", "edge_routes", "edge_animation", "colour", "narrative_labels"],
    });
  });

  it("fails closed for a synthetic replay", async () => {
    const replay = await load(syntheticUrl);
    expect(() => buildCollaborationEvidenceGraph(replay)).toThrow(/verified commit-pinned/);
  });

  it("declares graph drill-through, truth, filters, and keyboard access in the shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('id="collaboration-graph"');
    expect(html).toContain('id="dossier-graph"');
    expect(html).toContain('id="interior-fact-graph"');
    expect(html).toContain("NO TYPE SUBSTITUTION");
    expect(html).toContain("PRESENTATION-ONLY");
    expect(html).toContain("G to open the typed evidence graph");
  });
});
