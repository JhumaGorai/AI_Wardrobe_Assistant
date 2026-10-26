"use client";

import { useEffect, useState } from "react";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/auth-token";

/**
 * Temporary dev shim for auth (see lib/auth-token.ts) -- shows a "paste your token" box until
 * one is saved, then a small "signed in" indicator. Every wardrobe page renders this and reacts
 * to `onTokenChange` instead of reading localStorage itself, so there's one place that owns the
 * "do we have a token yet" state.
 */
export function TokenBar({ onTokenChange }: { onTokenChange?: (token: string | null) => void }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = getStoredToken();
    setTokenState(stored);
    setHydrated(true);
    onTokenChange?.(stored);
    // Only run once on mount -- onTokenChange is a fresh closure every render in the callers
    // below, so including it here would create a render loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!hydrated) return null;

  if (token) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-md border border-neutral-200 bg-neutral-50 px-4 py-2 text-sm">
        <span className="text-neutral-600">Signed in (access token saved in this browser)</span>
        <button
          type="button"
          className="text-red-600 underline"
          onClick={() => {
            clearStoredToken();
            setTokenState(null);
            onTokenChange?.(null);
          }}
        >
          Clear token
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-neutral-200 bg-neutral-50 p-4 text-sm">
      <p className="text-neutral-600">
        No login page yet (that&apos;s Phase 18) &mdash; sign up or log in via{" "}
        <a
          className="underline"
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
        >
          the API docs
        </a>
        , copy the <code>access_token</code> from the response, and paste it here.
      </p>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-neutral-300 px-2 py-1"
          placeholder="Paste access token"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="button"
          className="rounded bg-neutral-900 px-3 py-1 text-white disabled:opacity-40"
          disabled={!draft.trim()}
          onClick={() => {
            const trimmed = draft.trim();
            setStoredToken(trimmed);
            setTokenState(trimmed);
            onTokenChange?.(trimmed);
            setDraft("");
          }}
        >
          Save token
        </button>
      </div>
    </div>
  );
}
