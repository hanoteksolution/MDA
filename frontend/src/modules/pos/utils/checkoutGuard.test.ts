/** FE-5: the POS blocks checkout when no branch/terminal shift is in place. */
import { describe, expect, it } from "vitest";
import { getCheckoutBlockReason } from "./checkoutGuard";

const openShift = { status: "open", terminal_id: "t1", branch_id: "b1" };

describe("getCheckoutBlockReason", () => {
  it("blocks when no branch is selected", () => {
    expect(getCheckoutBlockReason({ branchId: null, terminalRequired: false, session: null })).toMatch(
      /single branch/i
    );
    expect(getCheckoutBlockReason({ branchId: undefined, terminalRequired: true, session: openShift })).toMatch(
      /single branch/i
    );
  });

  it("blocks the 'all branches' selector", () => {
    expect(getCheckoutBlockReason({ branchId: "all", terminalRequired: false, session: null })).toMatch(
      /single branch/i
    );
  });

  it("blocks a terminal branch until a shift is open", () => {
    expect(getCheckoutBlockReason({ branchId: "b1", terminalRequired: true, session: null })).toMatch(
      /open a shift/i
    );
    expect(
      getCheckoutBlockReason({
        branchId: "b1",
        terminalRequired: true,
        session: { ...openShift, status: "closed" },
      })
    ).toMatch(/open a shift/i);
  });

  it("blocks a shift that has no terminal, and one from another branch", () => {
    expect(
      getCheckoutBlockReason({
        branchId: "b1",
        terminalRequired: true,
        session: { status: "open", terminal_id: null, branch_id: "b1" },
      })
    ).toMatch(/not attached to a terminal/i);
    expect(getCheckoutBlockReason({ branchId: "b2", terminalRequired: true, session: openShift })).toMatch(
      /another branch/i
    );
  });

  it("allows a sale inside an open terminal shift", () => {
    expect(getCheckoutBlockReason({ branchId: "b1", terminalRequired: true, session: openShift })).toBeNull();
  });

  it("keeps legacy branches (no terminal configured) working without a shift", () => {
    expect(getCheckoutBlockReason({ branchId: "b1", terminalRequired: false, session: null })).toBeNull();
  });
});
