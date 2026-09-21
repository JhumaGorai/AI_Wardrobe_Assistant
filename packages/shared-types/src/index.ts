/**
 * Types shared between frontend and (conceptually) the backend's Pydantic schemas.
 * Keep these in sync with apps/api/app/schemas/* by hand for the MVP — add codegen later if it
 * becomes a real pain point, not before.
 */

export interface User {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: "bearer";
  user: User;
}
