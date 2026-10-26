"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { TokenBar } from "@/components/TokenBar";
import { ApiError } from "@/lib/api/client";
import { uploadGarment } from "@/lib/api/garments";

export default function UploadGarmentPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token || !file) return;
    setSubmitting(true);
    setError(null);
    try {
      const garment = await uploadGarment(token, file, name.trim() || undefined);
      router.push(`/wardrobe/${garment.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? describeUploadError(err) : "Upload failed.");
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-md flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">Upload a garment</h1>

      <TokenBar onTokenChange={setToken} />

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Photo
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Name (optional)
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded border border-neutral-300 px-2 py-1"
            placeholder="e.g. Favorite denim jacket"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={!token || !file || submitting}
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          {submitting ? "Uploading…" : "Upload"}
        </button>
        <p className="text-xs text-neutral-500">
          Analysis (category, colors, style tags, ...) runs in the background with a mock AI
          provider — open the garment page in a second or two to see it filled in.
        </p>
      </form>
    </main>
  );
}

function describeUploadError(err: ApiError): string {
  if (err.status === 401) return "Your token is missing, invalid, or expired. Paste a fresh one above.";
  if (err.status === 415) return "That file type isn't supported — use JPEG, PNG, or WebP.";
  if (err.status === 413) return "That image is too large (10MB max).";
  if (err.status === 400) return "That file looks empty.";
  return "Upload failed.";
}
