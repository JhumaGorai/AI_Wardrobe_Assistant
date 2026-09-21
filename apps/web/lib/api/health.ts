import { getApiRootUrl } from "@/lib/api/base-url";

export async function getHealth(): Promise<{ ok: boolean }> {
  try {
    const response = await fetch(`${getApiRootUrl()}/health`, { cache: "no-store" });
    if (!response.ok) return { ok: false };
    const data = await response.json();
    return { ok: data?.status === "ok" };
  } catch {
    return { ok: false };
  }
}
