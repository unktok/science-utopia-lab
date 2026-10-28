export const stableStringify = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    const row = value as Record<string, unknown>;
    return `{${Object.keys(row).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(row[key])}`).join(",")}}`;
  }
  const scalar = JSON.stringify(value);
  if (scalar === undefined) throw new Error("Canonical JSON cannot encode undefined");
  return scalar;
};

export async function canonicalHash(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(stableStringify(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

const webValue = (value: unknown): unknown => {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Web canonical JSON cannot encode a non-finite number");
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) throw new Error("Web canonical JSON cannot encode an unsafe integer");
    const bytes = new Uint8Array(8);
    new DataView(bytes.buffer).setFloat64(0, value, false);
    const bits = [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
    return { $number_f64: bits };
  }
  if (Array.isArray(value)) return value.map(webValue);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, webValue(item)]));
  return value;
};

export async function webCanonicalHash(value: unknown): Promise<string> {
  return canonicalHash(webValue(value));
}
