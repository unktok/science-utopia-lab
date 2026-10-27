/// <reference types="vite/client" />

declare global {
  interface WindowEventMap {
    "noctiluca:select": CustomEvent<import("./types").SelectionDetail>;
    "noctiluca:renderer-ready": CustomEvent<void>;
    "noctiluca:asset-missing": CustomEvent<{ key: string; entityId: string }>;
  }
}

export {};
