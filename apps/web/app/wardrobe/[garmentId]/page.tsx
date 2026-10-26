"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { TokenBar } from "@/components/TokenBar";
import { ApiError } from "@/lib/api/client";
import { deleteGarment, Garment, getGarment, updateGarment } from "@/lib/api/garments";

const CATEGORIES = ["top", "bottom", "dress", "outerwear", "footwear", "accessory"];

export default function GarmentDetailPage() {
  const params = useParams<{ garmentId: string }>();
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [garment, setGarment] = useState<Garment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load(activeToken: string) {
    setError(null);
    try {
      const result = await getGarment(activeToken, params.garmentId);
      setGarment(result);
      setEditName(result.name ?? "");
      setEditCategory(result.category ?? "");
    } catch (err) {
      setGarment(null);
      setError(
        err instanceof ApiError && err.status === 404
          ? "Garment not found."
          : "Could not load this garment."
      );
    }
  }

  async function handleSave() {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateGarment(token, params.garmentId, {
        name: editName.trim() || undefined,
        category: editCategory || undefined,
      });
      setGarment(updated);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 422
          ? "That category isn't one of the allowed values."
          : "Could not save changes."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!token) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteGarment(token, params.garmentId);
      router.push("/wardrobe");
    } catch {
      setError("Could not delete this garment.");
      setDeleting(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-8">
      <Link href="/wardrobe" className="text-sm text-neutral-500 underline">
        ← Back to wardrobe
      </Link>

      <TokenBar
        onTokenChange={(next) => {
          setToken(next);
          if (next) load(next);
          else setGarment(null);
        }}
      />

      {error && <p className="text-sm text-red-600">{error}</p>}

      {garment && (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-6 sm:flex-row">
            <div className="h-48 w-48 shrink-0 overflow-hidden rounded bg-neutral-100">
              {garment.images[0] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={garment.images[0].image_url}
                  alt={garment.name ?? "Garment"}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-xs text-neutral-400">
                  No image
                </div>
              )}
            </div>
            <div className="flex flex-col gap-1 text-sm">
              <p>
                Status: <span className="font-medium">{garment.processing_status}</span>
              </p>
              {garment.processing_error && <p className="text-red-600">{garment.processing_error}</p>}
              <p>Category: {garment.category ?? "—"}</p>
              <p>Subcategory: {garment.subcategory ?? "—"}</p>
              <p>Colors: {garment.colors.length ? garment.colors.join(", ") : "—"}</p>
              <p>Pattern: {garment.pattern ?? "—"}</p>
              <p>Material: {garment.material ?? "—"}</p>
              <p>Fit: {garment.fit ?? "—"}</p>
              <p>Formality: {garment.formality ?? "—"}</p>
              <p>Seasons: {garment.seasons.length ? garment.seasons.join(", ") : "—"}</p>
              <p>Style tags: {garment.style_tags.length ? garment.style_tags.join(", ") : "—"}</p>
              <p>Description: {garment.description ?? "—"}</p>
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-4">
            <h2 className="text-sm font-semibold">Edit</h2>
            <label className="flex flex-col gap-1 text-sm">
              Name
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="rounded border border-neutral-300 px-2 py-1"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Category
              <select
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                className="rounded border border-neutral-300 px-2 py-1"
              >
                <option value="">—</option>
                {CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white disabled:opacity-40"
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-600 disabled:opacity-40"
              >
                {deleting ? "Deleting…" : "Delete garment"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
