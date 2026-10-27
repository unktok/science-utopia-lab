import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  agentLocation,
  deriveSummary,
  eventDescription,
  frameAt,
  validateReplay,
} from "../src/model.js";

const payload = JSON.parse(await readFile(new URL("../data/one-year.replay.json", import.meta.url)));

test("generated fixture satisfies the replay-view contract", () => {
  const data = validateReplay(payload);
  assert.equal(data.events.length, 11);
  assert.equal(frameAt(data, 999).cursor, 11);
  assert.equal(frameAt(data, -1).cursor, 0);
});

test("summary is derived only from projected state", () => {
  const { frame } = frameAt(payload, payload.events.length);
  assert.deepEqual(deriveSummary(frame.state), {
    researchers: 2,
    activeResearchers: 2,
    totalResources: 200,
    papers: 1,
    accepted: 1,
  });
});

test("event presentation does not mutate or reinterpret domain state", () => {
  const review = payload.events.find((event) => event.event_type === "review.completed");
  assert.equal(agentLocation(review, "researcher-b"), "forum");
  assert.match(eventDescription(review), /score 4/);
  assert.equal(payload.frames.at(-1).state.artifacts["paper-1"].reviews.length, 1);
});

test("mismatched canonical event and projected frame is rejected", () => {
  const broken = structuredClone(payload);
  broken.frames[1].event_id = "wrong";
  assert.throws(() => validateReplay(broken), /does not match/);
});
