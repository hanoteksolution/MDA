/**
 * How a secret gets from a form field to the encrypted store — and what is left afterwards.
 *
 * The secret exists only in the draft while the user types. `commitCredential` sends it once
 * (create or rotate) and the caller must then blank the draft; the API never returns it, so
 * there is nothing to show, prefill or re-send on the next edit.
 */
import type { IntegrationCredential } from "@/services/api/integrations";
import { validateCredentialForm } from "./lib";

export interface CredentialDraft {
  /** "existing": use the selected credential (optionally rotating its secret). "new": create one. */
  mode: "existing" | "new";
  label: string;
  /** New secret (mode "new") or replacement secret (mode "existing"). Never prefilled. */
  secret: string;
}

export const emptyCredentialDraft = (): CredentialDraft => ({ mode: "existing", label: "", secret: "" });

/** Same draft with the secret wiped — apply after every submit attempt, success or not. */
export const scrubDraft = (draft: CredentialDraft): CredentialDraft => ({ ...draft, secret: "" });

export interface CredentialApi {
  create: (input: { label: string; secret: string }) => Promise<{ data: IntegrationCredential }>;
  rotate: (id: string, input: { secret?: string; label?: string }) => Promise<{ data: IntegrationCredential }>;
}

export class CredentialDraftError extends Error {
  fieldErrors: Record<string, string>;
  constructor(fieldErrors: Record<string, string>) {
    super(Object.values(fieldErrors)[0] ?? "Invalid credential.");
    this.fieldErrors = fieldErrors;
  }
}

/** Returns the credential id to link (or null for none). Sends the secret at most once. */
export async function commitCredential(
  selectedId: string,
  draft: CredentialDraft,
  api: CredentialApi
): Promise<string | null> {
  if (draft.mode === "new") {
    const errors = validateCredentialForm(draft);
    if (Object.keys(errors).length) throw new CredentialDraftError(errors);
    const res = await api.create({ label: draft.label.trim(), secret: draft.secret });
    return res.data.id;
  }
  if (selectedId && draft.secret.trim()) {
    await api.rotate(selectedId, { secret: draft.secret });
  }
  return selectedId || null;
}
