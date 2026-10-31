import { describe, expect, it } from "vitest";
import { designRequest, nativeEngineeringLoss } from "../src/nativeJobs";

describe("explicit native design submission", () => {
  it("keeps parent, edited system and explicit editable loss separate", () => {
    const parent = { metadata: { label: "original" } };
    const request = designRequest(parent, JSON.stringify({ metadata: { label: "edited" } }), JSON.stringify(nativeEngineeringLoss), 1301, 2);
    expect(request.parent_system).toEqual(parent);
    expect(request.system).not.toEqual(parent);
    expect(request.loss_spec).toEqual(nativeEngineeringLoss);
    expect(Object.keys(request).sort()).toEqual(["loss_spec", "parent_system", "seed", "system", "years"]);
    expect(parent.metadata.label).toBe("original");
  });
  it("rejects non-object input rather than treating it as executable commands", () => {
    expect(() => designRequest({}, '"command"', "{}", 1301, 2)).toThrow("JSON objects");
    expect(() => designRequest({}, "{}", "{}", 1301, 2.5)).toThrow("Integer");
    expect(() => designRequest({}, "not JSON", "{}", 1301, 2)).toThrow();
  });
});
