import { ApiError, apiFetch } from "@/lib/api/client";
import { getApiV1BaseUrl } from "@/lib/api/base-url";

export interface GarmentImage {
  id: string;
  image_url: string;
  image_type: string;
  is_primary: boolean;
  width: number | null;
  height: number | null;
  created_at: string;
}

export type ProcessingStatus = "pending" | "completed" | "failed";

export interface Garment {
  id: string;
  user_id: string;
  name: string | null;
  category: string | null;
  subcategory: string | null;
  colors: string[];
  pattern: string | null;
  material: string | null;
  fit: string | null;
  formality: number | null;
  seasons: string[];
  style_tags: string[];
  description: string | null;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  images: GarmentImage[];
}

export interface GarmentUpdateInput {
  name?: string;
  category?: string;
  subcategory?: string;
  colors?: string[];
  pattern?: string;
  material?: string;
  fit?: string;
  formality?: number;
  seasons?: string[];
  style_tags?: string[];
  description?: string;
}

export async function listGarments(token: string): Promise<Garment[]> {
  return apiFetch<Garment[]>("/garments", { method: "GET", token });
}

export async function getGarment(token: string, id: string): Promise<Garment> {
  return apiFetch<Garment>(`/garments/${id}`, { method: "GET", token });
}

export async function updateGarment(
  token: string,
  id: string,
  payload: GarmentUpdateInput
): Promise<Garment> {
  return apiFetch<Garment>(`/garments/${id}`, { method: "PUT", token, body: payload });
}

export async function deleteGarment(token: string, id: string): Promise<void> {
  await apiFetch<void>(`/garments/${id}`, { method: "DELETE", token });
}

/**
 * Upload is multipart/form-data, unlike every other call in this module -- apiFetch always
 * JSON-encodes its body, so this builds the request directly instead of going through it.
 */
export async function uploadGarment(token: string, file: File, name?: string): Promise<Garment> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);

  const response = await fetch(`${getApiV1BaseUrl()}/garments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, payload);
  }
  return payload as Garment;
}
