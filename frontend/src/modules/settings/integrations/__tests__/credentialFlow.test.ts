import { describe, expect, it, vi } from "vitest";
import { CredentialDraftError, commitCredential, emptyCredentialDraft, scrubDraft } from "../credentialFlow";

const cred = (id: string) => ({ data: { id, label: "L", has_secret: true, masked_tail: "", rotated_at: null } });
const api = () => ({ create: vi.fn().mockResolvedValue(cred("new-id")), rotate: vi.fn().mockResolvedValue(cred("sel")) });

describe("credential draft flow", () => {
  it("creates a new credential and returns only its id", async () => {
    const a = api();
    const id = await commitCredential("", { mode: "new", label: " Gateway ", secret: "s3cret-value" }, a);
    expect(id).toBe("new-id");
    expect(a.create).toHaveBeenCalledWith({ label: "Gateway", secret: "s3cret-value" });
    expect(a.rotate).not.toHaveBeenCalled();
  });

  it("validates a new credential before any request", async () => {
    const a = api();
    await expect(commitCredential("", { mode: "new", label: "", secret: "" }, a)).rejects.toBeInstanceOf(CredentialDraftError);
    expect(a.create).not.toHaveBeenCalled();
  });

  it("keeps the existing secret when no replacement is typed", async () => {
    const a = api();
    expect(await commitCredential("sel", emptyCredentialDraft(), a)).toBe("sel");
    expect(a.rotate).not.toHaveBeenCalled();
    expect(a.create).not.toHaveBeenCalled();
  });

  it("rotates only when a replacement secret is typed", async () => {
    const a = api();
    expect(await commitCredential("sel", { mode: "existing", label: "", secret: "fresh-secret" }, a)).toBe("sel");
    expect(a.rotate).toHaveBeenCalledWith("sel", { secret: "fresh-secret" });
  });

  it("returns null when no credential is selected", async () => {
    expect(await commitCredential("", emptyCredentialDraft(), api())).toBeNull();
  });

  it("scrubs the secret from the draft but keeps the rest", () => {
    expect(scrubDraft({ mode: "new", label: "L", secret: "s3cret" })).toEqual({ mode: "new", label: "L", secret: "" });
  });
});
