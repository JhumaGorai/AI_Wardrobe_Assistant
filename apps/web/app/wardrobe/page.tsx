"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { TokenBar } from "@/components/TokenBar";
import { ApiError } from "@/lib/api/client";
import { Garment, listGarments } from "@/lib/api/garments";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function WardrobePage() {
  const [token, setToken] = useState<string | null>(null);
  const [garments, setGarments] = useState<Garment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (activeToken: string) => {
    setError(null);
    try {
      const result = await listGarments(activeToken);
      setGarments(result);
    } catch (err) {
      setGarments(null);
      setError(
        err instanceof ApiError && err.status === 401
          ? "Your token is missing, invalid, or expired. Paste a fresh one."
          : "Could not load your wardrobe."
      );
    }
  }, []);

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Your wardrobe</h1>
        <Link href="/wardrobe/upload" className="rounded bg-neutral-900 px-4 py-2 text-sm text-white">
          Upload a garment
        </Link>
      </div>

      <TokenBar
        onTokenChange={(next) => {
          setToken(next);
          if (next) refresh(next);
          else setGarments(null);
        }}
      />

      {!token && (
        <p className="text-sm text-neutral-500">Paste an access token above to load your wardrobe.</p>
      )}

      {token && error && <p className="text-sm text-red-600">{error}</p>}

      {token && !error && garments === null && <p className="text-sm text-neutral-500">Loading…</p>}

      {token && garments !== null && garments.length === 0 && (
        <p className="text-sm text-neutral-500">
          No garments yet.{" "}
          <Link className="underline" href="/wardrobe/upload">
            Upload your first one
          </Link>
          .
        </p>
      )}

      {garments && garments.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {garments.map((garment) => (
            <Link
              key={garment.id}
              href={`/wardrobe/${garment.id}`}
              className="group flex flex-col gap-2 rounded-lg border border-neutral-200 p-3 transition hover:border-neutral-400"
            >
              <div className="aspect-square overflow-hidden rounded bg-neutral-100">
                {garment.images[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={garment.images[0].image_url}
                    alt={garment.name ?? garment.category ?? "Garment"}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-xs text-neutral-400">
                    No image
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium">
                  {garment.name ?? garment.category ?? "Untitled"}
                </span>
                <span
                  className={`shrink-0 rounded px-2 py-0.5 text-xs ${
                    STATUS_STYLES[garment.processing_status] ?? "bg-neutral-100 text-neutral-600"
                  }`}
                >
                  {garment.processing_status}
                </span>
              </div>
              {garment.style_tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {garment.style_tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
