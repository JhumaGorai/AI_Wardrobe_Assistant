/**
 * Temporary dev shim: the frontend has no login/signup pages yet (those are Phase 18), so for
 * now a user signs up/logs in via the API docs (http://localhost:8000/docs) and pastes the
 * resulting access_token here. It's stored in this browser's localStorage only -- never sent
 * anywhere except as the Authorization header on requests to this app's own API (see
 * lib/api/garments.ts). Replace this whole module once real login/signup pages exist.
 */
const STORAGE_KEY = "wardrobe_access_token";

export function getStoredToken(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Storage can throw (private browsing, disabled storage, ...) -- the token just won't
    // persist across reloads, which is an acceptable degradation for this temporary shim.
  }
}

export function clearStoredToken(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // see setStoredToken
  }
}
