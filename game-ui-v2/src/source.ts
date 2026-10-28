export const REPLAY_SOURCES = {
  campaign: "/data/completed-campaign.replay.json",
  synthetic: "/data/vertical-slice.replay.json",
} as const;

export type ReplaySource = keyof typeof REPLAY_SOURCES;

export function replaySource(search: string): { key: ReplaySource; url: string } {
  const requested = new URLSearchParams(search).get("replay") ?? "campaign";
  if (!(requested in REPLAY_SOURCES)) {
    throw new Error(`Unknown replay source ${requested}; allowed: ${Object.keys(REPLAY_SOURCES).join(", ")}`);
  }
  const key = requested as ReplaySource;
  return { key, url: REPLAY_SOURCES[key] };
}
