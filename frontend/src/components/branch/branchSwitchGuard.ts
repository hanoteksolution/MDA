/**
 * Lets a screen with unsaved branch-bound work (a POS cart) veto a branch switch.
 * `warning` returns a message to confirm (or null when switching is safe); `discard` runs once
 * the user confirms, so that work cannot follow the user into another branch.
 */
export interface BranchSwitchGuard {
  warning: () => string | null;
  discard?: () => void;
}

let guard: BranchSwitchGuard | null = null;

export function setBranchSwitchGuard(next: BranchSwitchGuard | null) {
  guard = next;
}

export function branchSwitchWarning(): string | null {
  try {
    return guard ? guard.warning() : null;
  } catch {
    return null;
  }
}

export function discardBranchBoundWork() {
  try {
    guard?.discard?.();
  } catch {
    /* discarding local work must never block the switch */
  }
}
