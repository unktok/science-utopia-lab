import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildResearcherLifeCourseProjection, dossierAtCursor } from "../src/researcherLifeCourse";
import { parseReplayV2 } from "../src/replay";

const campaignUrl = new URL("../public/data/completed-campaign.replay.json", import.meta.url);
const syntheticUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const pageUrl = new URL("../index.html", import.meta.url);
const load = async (url = campaignUrl) => parseReplayV2(JSON.parse(await readFile(fileURLToPath(url), "utf8")));

describe("verified researcher identity and life-course projection", () => {
  it("builds one evidence-bounded dossier per canonical researcher", async () => {
    const projection = buildResearcherLifeCourseProjection(await load());
    expect(projection.truth_status).toBe("verified_replay");
    expect(projection.dossiers).toHaveLength(12);
    const author = projection.dossiers.find((dossier) => dossier.researcher_id === "institution_0000_researcher_2")!;
    expect(author.authored_artifact_ids).toEqual(["https://arxiv.org/abs/1606.04422"]);
    expect(author.authored_topics).toContain("Machine Learning");
    expect(author.observed_years).toEqual([0, 1]);
    expect(author.missingness.join(" ")).toContain("No explicit researcher.exit event");
  });

  it("shows cursor-bounded resource state and inactive year-close state without inventing exit", async () => {
    const projection = buildResearcherLifeCourseProjection(await load());
    const dossier = projection.dossiers.find((candidate) => candidate.researcher_id === "institution_0000_researcher_0")!;
    const beforeClose = dossierAtCursor(projection, dossier, 44_999);
    const afterClose = dossierAtCursor(projection, dossier, 45_001);
    expect(beforeClose.agent_state).toMatchObject({ active: true, balance: 7 });
    expect(afterClose.agent_state).toMatchObject({ active: false, balance: 7 });
    expect(afterClose.resource_points.map((point) => point.balance)).toEqual([50, 40, 29, 18, 7, 7]);
    expect(dossier.events.some(({ event }) => event.kind === "researcher.exit")).toBe(false);
  });

  it("keeps artifact-mediated peer evidence canonical while leaving line layout to presentation", async () => {
    const projection = buildResearcherLifeCourseProjection(await load());
    const reviewer = projection.dossiers.find((dossier) => dossier.researcher_id === "institution_0001_researcher_1")!;
    expect(reviewer.relationships).toContainEqual(expect.objectContaining({
      truth_status: "canonical_evidence",
      peer_id: "institution_0000_researcher_2",
      event_kind: "review.completed",
      artifact_id: "https://arxiv.org/abs/1606.04422",
    }));
    expect(reviewer.authored_topics).toEqual([]);
  });

  it("is invariant to all choreography and ambient presentation records", async () => {
    const replay = await load();
    const summarize = () => buildResearcherLifeCourseProjection(replay).dossiers.map((dossier) => ({
      id: dossier.researcher_id,
      events: dossier.events.map(({ event, frame }) => [event.id, frame.cursor]),
      resources: dossier.resource_points,
      topics: dossier.authored_topics,
      relationships: dossier.relationships,
    }));
    const baseline = summarize();
    replay.choreography.actions = [];
    replay.choreography.flows = [];
    replay.choreography.epistemic_flows = [];
    replay.choreography.interior_activities = [];
    replay.ambient.actors = [];
    replay.ambient.effects = [];
    expect(summarize()).toEqual(baseline);
  });

  it("fails closed for synthetic sources", async () => {
    const replay = await load(syntheticUrl);
    expect(() => buildResearcherLifeCourseProjection(replay)).toThrow(/verified commit-pinned/);
  });

  it("declares dossier drill-down, missingness, and keyboard boundaries in the shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('id="researcher-dossier"');
    expect(html).toContain('id="interior-fact-researcher"');
    expect(html).toContain("VERIFIED RESEARCHER DOSSIER");
    expect(html).toContain("PRESENTATION-ONLY");
    expect(html).toContain("OBSERVATION LIMITS / MISSINGNESS");
    expect(html).toContain("D to open a researcher dossier");
  });
});
