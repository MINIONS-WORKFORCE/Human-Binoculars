/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin, e.g. http://127.0.0.1:8000. Empty means same origin. */
  readonly VITE_API_BASE_URL?: string;
  /** "false" turns MSW off in dev; "true" turns it on in a production build. */
  readonly VITE_USE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
