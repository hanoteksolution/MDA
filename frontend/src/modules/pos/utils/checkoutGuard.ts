import { ALL_BRANCHES } from "@/services/api/branchContext";

/**
 * Whether the POS may start a checkout right now (FE-5).
 *
 * This is a usability guard only — the backend refuses the same sale regardless
 * (`CashierSessionService.checkout_context`). It exists so the cashier is told *why*
 * instead of getting a rejected request after tendering payment.
 */
export interface CheckoutGuardInput {
  /** The branch the POS is acting in; `null`/"all" means none is selected. */
  branchId: string | null | undefined;
  /** True once the branch has at least one active terminal (POS is then enforced). */
  terminalRequired: boolean;
  /** The cashier's open shift in this branch, if any. */
  session: { status: string; terminal_id?: string | null; branch_id?: string } | null | undefined;
}

export function getCheckoutBlockReason(input: CheckoutGuardInput): string | null {
  const { branchId, terminalRequired, session } = input;
  if (!branchId || branchId === ALL_BRANCHES) {
    return "Select a single branch before selling.";
  }
  const open = session && session.status === "open" ? session : null;
  if (open && open.branch_id && open.branch_id !== branchId) {
    return "Your open shift belongs to another branch. Switch back or close it first.";
  }
  if (terminalRequired && !open) {
    return "Open a shift on a POS terminal before selling.";
  }
  if (terminalRequired && open && !open.terminal_id) {
    return "This shift is not attached to a terminal. Close it and open a new shift.";
  }
  return null;
}
