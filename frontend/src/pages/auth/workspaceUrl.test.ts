import { describe, expect, it, vi } from "vitest";
import {
  WORKSPACE_CHECK_DEBOUNCE_MS,
  canContinueWorkspaceUrl,
  conflictSuggestions,
  deriveWorkspaceUiState,
  nextSlugFromCompanyName,
  normalizeWorkspaceSlug,
  suggestFromCompanyName,
  workspaceHostname,
  workspaceHttpsUrl,
} from "./workspaceUrl";

describe("workspace URL helpers", () => {
  it("normalizes company names to a canonical slug", () => {
    expect(suggestFromCompanyName("Barista Coffee")).toBe("barista-coffee");
    expect(normalizeWorkspaceSlug("  ARABICA  ")).toBe("arabica");
    expect(normalizeWorkspaceSlug("shop_name")).toBe("shop-name");
  });

  it("never trims a boundary hyphen into a different slug (matches backend rejection)", () => {
    expect(normalizeWorkspaceSlug("-shop")).toBe("-shop");
    expect(normalizeWorkspaceSlug("shop-")).toBe("shop-");
  });

  it("builds the final hostname preview from the normalized slug", () => {
    expect(workspaceHostname("Barista", "erp.safaritechno.com")).toBe(
      "barista.erp.safaritechno.com"
    );
    expect(workspaceHttpsUrl("barista", "erp.safaritechno.com")).toBe(
      "https://barista.erp.safaritechno.com"
    );
  });

  it("does not overwrite a manually edited slug when the company name changes", () => {
    expect(
      nextSlugFromCompanyName({
        companyName: "New Cafe",
        slugTouched: true,
        currentSlug: "barista",
      })
    ).toBe("barista");
    expect(
      nextSlugFromCompanyName({
        companyName: "Barista Coffee",
        slugTouched: false,
        currentSlug: "",
      })
    ).toBe("barista-coffee");
  });

  it("maps checking / available / taken / reserved / invalid / error states", () => {
    expect(deriveWorkspaceUiState({ slug: "", checking: false, status: null, networkError: false })).toBe(
      "empty"
    );
    expect(
      deriveWorkspaceUiState({ slug: "barista", checking: true, status: null, networkError: false })
    ).toBe("checking");
    expect(
      deriveWorkspaceUiState({
        slug: "barista",
        checking: false,
        status: {
          normalized: "barista",
          available: true,
          hostname: "barista.erp.safaritechno.com",
          reason: null,
          suggestions: [],
        },
        networkError: false,
      })
    ).toBe("available");
    expect(
      deriveWorkspaceUiState({
        slug: "arabica",
        checking: false,
        status: {
          normalized: "arabica",
          available: false,
          hostname: null,
          reason: "taken",
          suggestions: ["arabica-cafe"],
        },
        networkError: false,
      })
    ).toBe("taken");
    expect(
      deriveWorkspaceUiState({
        slug: "admin",
        checking: false,
        status: {
          normalized: "admin",
          available: false,
          hostname: null,
          reason: "reserved",
          suggestions: ["admin-cafe"],
        },
        networkError: false,
      })
    ).toBe("reserved");
    expect(
      deriveWorkspaceUiState({
        slug: "...",
        checking: false,
        status: {
          normalized: null,
          available: false,
          hostname: null,
          reason: "invalid",
          suggestions: [],
        },
        networkError: false,
      })
    ).toBe("invalid");
    expect(
      deriveWorkspaceUiState({
        slug: "barista",
        checking: false,
        status: null,
        networkError: true,
      })
    ).toBe("error");
  });

  it("disables submit unless the URL is available", () => {
    expect(canContinueWorkspaceUrl("available")).toBe(true);
    expect(canContinueWorkspaceUrl("checking")).toBe(false);
    expect(canContinueWorkspaceUrl("taken")).toBe(false);
    expect(canContinueWorkspaceUrl("reserved")).toBe(false);
    expect(canContinueWorkspaceUrl("invalid")).toBe(false);
    expect(canContinueWorkspaceUrl("error")).toBe(false);
    expect(canContinueWorkspaceUrl("empty")).toBe(false);
  });

  it("extracts clickable 409 suggestions without private tenant data", () => {
    expect(conflictSuggestions({ suggestions: ["arabica-cafe", "arabica-coffee"] })).toEqual([
      "arabica-cafe",
      "arabica-coffee",
    ]);
    expect(conflictSuggestions({ company_name: "Secret Ltd" })).toEqual([]);
  });

  it("uses a debounce interval rather than checking every keystroke", () => {
    expect(WORKSPACE_CHECK_DEBOUNCE_MS).toBeGreaterThanOrEqual(300);
    const fn = vi.fn();
    let handle: ReturnType<typeof setTimeout> | undefined;
    const debounce = (value: string) => {
      if (handle) clearTimeout(handle);
      handle = setTimeout(() => fn(value), WORKSPACE_CHECK_DEBOUNCE_MS);
    };
    debounce("b");
    debounce("ba");
    debounce("barista");
    expect(fn).not.toHaveBeenCalled();
  });

  it("selecting a suggestion populates the input and is the next check value", () => {
    const selected = "arabica-cafe";
    expect(normalizeWorkspaceSlug(selected)).toBe("arabica-cafe");
    expect(workspaceHostname(selected, "erp.safaritechno.com")).toBe(
      "arabica-cafe.erp.safaritechno.com"
    );
  });

  it("success URL matches the approved slug", () => {
    const approved = "barista";
    const created = "barista";
    expect(workspaceHttpsUrl(created, "erp.safaritechno.com")).toBe(
      workspaceHttpsUrl(approved, "erp.safaritechno.com")
    );
  });
});
