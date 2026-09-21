/**
 * Resolves the API base URL depending on where the code runs.
 *
 * In Docker, this app's server-side code (Server Components, Route Handlers) executes inside
 * the `web` container, where `localhost` refers to that container itself — the API is only
 * reachable there via the compose service name `api`. Code running in the browser, on the other
 * hand, is outside Docker entirely and must use a host-reachable URL (`localhost`).
 *
 * So: server-side code uses INTERNAL_API_BASE_URL (server-only env var, not exposed to the
 * browser), and browser code uses NEXT_PUBLIC_API_BASE_URL.
 */
export function getApiV1BaseUrl(): string {
  if (typeof window === "undefined") {
    return (
      process.env.INTERNAL_API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "http://localhost:8000/api/v1"
    );
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
}

export function getApiRootUrl(): string {
  return getApiV1BaseUrl().replace(/\/api\/v1\/?$/, "");
}
