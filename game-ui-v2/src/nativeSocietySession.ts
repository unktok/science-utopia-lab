import { adoptionConfirmation, type AdoptionCandidate, type AdoptionReceipt, type AdoptionTransport } from "./designLifecycleContract";

export interface SocietyObservation {
  observation_id: string; through_year: number; after_year: number; system_fingerprint: string; loss: number;
  measurement: Record<string, unknown>; preceding_adoption: string | null; comparison: "online-same-society-not-counterfactual";
}
export interface SocietyAdoption {
  request_id: string; request_sha256: string; candidate_fingerprint: string; after_year: number; migration_receipt_sha256: string;
}
export interface SocietyConfirmation { request_id: string; request_sha256: string }
export interface SocietyRequest extends AdoptionCandidate {
  session_binding_sha256: string; observed_society_sha256: string; domain_sha256: string; patch: Record<string, unknown>;
}
export interface NativeSocietyProjection {
  schema: "scienceutopia.native-society-design-session.v1";
  binding: Record<string, unknown>; actual_society_binding: Record<string, unknown> | null; loss_spec: Record<string, unknown>;
  observations: SocietyObservation[]; requests: SocietyRequest[]; adoptions: SocietyAdoption[]; cancellations: unknown[];
  pending: SocietyRequest | null; journal_sha256: string | null; model_weights_trained: false; causal_improvement_established: false;
  confirmations: SocietyConfirmation[];
}

const SHA256 = /^[0-9a-f]{64}$/;
const object = (value: unknown, label: string): Record<string, any> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, any>;
};
const sha = (value: unknown, label: string): string => {
  if (typeof value !== "string" || !SHA256.test(value)) throw new Error(`${label} must be a lowercase 64-hex SHA256`);
  return value;
};

export function parseNativeSocietyProjection(value: unknown): NativeSocietyProjection {
  const data = object(value, "same-society projection");
  if (data.schema !== "scienceutopia.native-society-design-session.v1") throw new Error("Unsupported same-society projection schema");
  if (data.model_weights_trained !== false || data.causal_improvement_established !== false) throw new Error("Unsupported training or causal-improvement claim");
  object(data.binding, "binding"); object(data.loss_spec, "loss_spec");
  if (data.actual_society_binding !== null) object(data.actual_society_binding, "actual_society_binding");
  if (!Array.isArray(data.observations) || !Array.isArray(data.requests) || !Array.isArray(data.adoptions) || !Array.isArray(data.cancellations ?? []) || !Array.isArray(data.confirmations)) throw new Error("Society journal collections are incomplete");
  let previousYear = 0;
  for (const [index, item] of data.observations.entries()) {
    const observation = object(item, `observation ${index}`);
    if (!Number.isInteger(observation.after_year) || !Number.isInteger(observation.through_year) || observation.after_year !== previousYear || observation.through_year <= observation.after_year) throw new Error("Observation intervals must be contiguous and increasing");
    if (typeof observation.loss !== "number" || !Number.isFinite(observation.loss)) throw new Error("Observed interval loss must be finite");
    if (observation.comparison !== "online-same-society-not-counterfactual") throw new Error("Observation comparison boundary changed");
    sha(observation.system_fingerprint, "system_fingerprint");
    if (observation.preceding_adoption !== null) sha(observation.preceding_adoption, "preceding_adoption");
    object(observation.measurement, "measurement");
    previousYear = observation.through_year;
  }
  const requests = new Map<string, Record<string, any>>();
  for (const item of data.requests) {
    const request = object(item, "staged request") as unknown as SocietyRequest;
    const confirmation = adoptionConfirmation(request);
    if (requests.has(confirmation.confirmed_request_sha256)) throw new Error("Duplicate staged request SHA256");
    sha(request.session_binding_sha256, "session_binding_sha256"); sha(request.observed_society_sha256, "observed_society_sha256"); sha(request.domain_sha256, "domain_sha256");
    object(request.patch, "patch");
    requests.set(confirmation.confirmed_request_sha256, request as unknown as Record<string, any>);
  }
  for (const item of data.adoptions) {
    const adoption = object(item, "adoption");
    sha(adoption.request_sha256, "adoption request_sha256"); sha(adoption.candidate_fingerprint, "adoption candidate_fingerprint"); sha(adoption.migration_receipt_sha256, "migration_receipt_sha256");
    const request = requests.get(adoption.request_sha256);
    if (!request || request.request_id !== adoption.request_id || request.candidate_fingerprint !== adoption.candidate_fingerprint) throw new Error("Adoption does not match a staged request");
  }
  const confirmations = new Set<string>();
  for (const item of data.confirmations) {
    const confirmation = object(item, "confirmation");
    const requestSha256 = sha(confirmation.request_sha256, "confirmation request_sha256");
    const request = requests.get(requestSha256);
    if (!request || request.request_id !== confirmation.request_id || confirmations.has(requestSha256)) throw new Error("Confirmation does not match one unique staged request");
    confirmations.add(requestSha256);
  }
  if (data.pending !== null) {
    const pending = adoptionConfirmation(data.pending as SocietyRequest);
    const request = requests.get(pending.confirmed_request_sha256);
    const pendingRecord = data.pending as Record<string, unknown>;
    if (!request || request.request_id !== pending.request_id ||
      request.candidate_fingerprint !== pending.candidate_fingerprint ||
      request.expected_checkpoint_sha256 !== pending.expected_checkpoint_sha256 ||
      request.loss_spec_sha256 !== pendingRecord.loss_spec_sha256 ||
      request.session_binding_sha256 !== pendingRecord.session_binding_sha256 ||
      request.observed_society_sha256 !== pendingRecord.observed_society_sha256 ||
      request.domain_sha256 !== pendingRecord.domain_sha256) {
      throw new Error("Pending request is not the exact staged request in the journal");
    }
    if (data.adoptions.some((item: any) => item.request_sha256 === pending.confirmed_request_sha256)) throw new Error("Adopted request cannot remain pending");
  }
  if (data.journal_sha256 !== null) sha(data.journal_sha256, "journal_sha256");
  return { ...data, cancellations: data.cancellations ?? [] } as NativeSocietyProjection;
}

export class SocietyApiUnavailable extends Error {}

export class NativeSocietyApi implements AdoptionTransport {
  private constructor(private readonly token: string, private readonly fetcher: typeof fetch) {}

  static async connect(fetcher: typeof fetch = fetch): Promise<NativeSocietyApi> {
    const response = await fetcher.call(globalThis, "/native-api/session", { method: "GET" });
    if (response.status === 404) throw new SocietyApiUnavailable("Local same-society service is not available");
    if (!response.ok) throw new Error(`Local session service ${response.status}`);
    const session = object(await response.json(), "native API session");
    if (typeof session.token !== "string" || !session.token) throw new Error("Local session token is missing");
    return new NativeSocietyApi(session.token, fetcher);
  }

  private async request(path: string, init: RequestInit = {}): Promise<unknown> {
    const response = await this.fetcher.call(globalThis, `/native-api/${path}`, { ...init, headers: { "X-Native-Lab-Token": this.token, ...(init.body === undefined ? {} : { "Content-Type": "application/json" }), ...(init.headers ?? {}) } });
    if (response.status === 404) throw new SocietyApiUnavailable("Same-society endpoint is not configured on this local server");
    if (!response.ok) throw new Error(`Local same-society service ${response.status}: ${(await response.text()).slice(0, 300)}`);
    return response.json();
  }

  async projection(): Promise<NativeSocietyProjection> { return parseNativeSocietyProjection(await this.request("society")); }

  async dispatch(candidate: AdoptionCandidate, confirmedRequestSha256: string): Promise<{ status: "pending"; request_id: string; request_sha256: string }> {
    const exact = adoptionConfirmation(candidate);
    if (exact.confirmed_request_sha256 !== confirmedRequestSha256) throw new Error("Confirmed request SHA256 changed before dispatch");
    return await this.request("society/confirm", { method: "POST", body: JSON.stringify({ request_id: exact.request_id, confirmed_request_sha256: confirmedRequestSha256 }) }) as { status: "pending"; request_id: string; request_sha256: string };
  }

  async receipt(requestId: string): Promise<AdoptionReceipt> {
    if (!requestId || requestId.includes("/") || requestId.includes("..")) throw new Error("Unsafe society request ID");
    return await this.request(`society/requests/${encodeURIComponent(requestId)}`) as AdoptionReceipt;
  }
}

export interface SocietyFixtureEnvelope { schema: "scienceutopia.native-society-session-ui-fixture.v1"; label: "SYNTHETIC UI FIXTURE / ACTIONS DISABLED"; projection: NativeSocietyProjection }

export function parseSocietyFixture(value: unknown): SocietyFixtureEnvelope {
  const envelope = object(value, "society fixture");
  if (envelope.schema !== "scienceutopia.native-society-session-ui-fixture.v1" || envelope.label !== "SYNTHETIC UI FIXTURE / ACTIONS DISABLED") throw new Error("Unlabelled society fixture rejected");
  return { schema: envelope.schema, label: envelope.label, projection: parseNativeSocietyProjection(envelope.projection) };
}

export function latestRecoverableAdoption(projection: NativeSocietyProjection): SocietyRequest | null {
  const adoption = projection.adoptions.at(-1);
  if (!adoption) return null;
  const request = projection.requests.find((item) => item.request_id === adoption.request_id && item.request_sha256 === adoption.request_sha256);
  if (!request || request.candidate_fingerprint !== adoption.candidate_fingerprint) return null;
  const confirmed = projection.confirmations.some((item) => item.request_id === request.request_id && item.request_sha256 === request.request_sha256);
  return confirmed ? request : null;
}
