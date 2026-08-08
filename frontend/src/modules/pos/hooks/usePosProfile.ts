import { useMemo } from "react";
import { useModules } from "@/hooks/useModules";
import type { PosProfile } from "@/services/api/pos";

export type PosProfileCode =
  | "RETAIL"
  | "SUPERMARKET"
  | "PHARMACY"
  | "CAFETERIA"
  | "RESTAURANT"
  | "GYM"
  | "HOTEL_SERVICE";

export interface PosCapabilities {
  waiters?: boolean;
  tables?: boolean;
  batches?: boolean;
  modifiers?: boolean;
  kitchen_ticket?: boolean;
  membership_skus?: boolean;
  charge_to_room?: boolean;
  expiry?: boolean;
  rx?: boolean;
}

const DEFAULT_CAPS: Record<PosProfileCode, PosCapabilities> = {
  RETAIL: { waiters: true, tables: false, batches: false, charge_to_room: false },
  SUPERMARKET: { waiters: false, tables: false, batches: false, charge_to_room: false },
  PHARMACY: {
    waiters: false,
    tables: false,
    batches: true,
    expiry: true,
    rx: true,
    charge_to_room: false,
  },
  CAFETERIA: { waiters: true, tables: true, batches: false, charge_to_room: false },
  RESTAURANT: {
    waiters: true,
    tables: true,
    batches: false,
    modifiers: true,
    kitchen_ticket: true,
    charge_to_room: false,
  },
  GYM: { waiters: false, tables: false, membership_skus: true, charge_to_room: false },
  HOTEL_SERVICE: {
    waiters: true,
    tables: true,
    batches: false,
    charge_to_room: true,
  },
};

function inferCode(modules: string[]): PosProfileCode {
  if (modules.includes("hotel") && (modules.includes("restaurant") || modules.includes("pos"))) {
    return "HOTEL_SERVICE";
  }
  if (modules.includes("restaurant")) return "RESTAURANT";
  if (modules.includes("pharmacy")) return "PHARMACY";
  if (modules.includes("gym")) return "GYM";
  return "RETAIL";
}

/** Resolve Universal POS profile code + capabilities from profile API + enabled modules. */
export function usePosProfile(profile: PosProfile | null | undefined) {
  const { modules, hasModule } = useModules();

  return useMemo(() => {
    const code = (profile?.code as PosProfileCode) || inferCode(modules);
    const capabilities: PosCapabilities = {
      ...(DEFAULT_CAPS[code] || DEFAULT_CAPS.RETAIL),
      ...(profile?.capabilities || {}),
    };
    if (hasModule("hotel")) {
      capabilities.charge_to_room = true;
    }
    return {
      code,
      capabilities,
      showTables: Boolean(capabilities.tables) && hasModule("restaurant"),
      showBatches: Boolean(capabilities.batches) && hasModule("pharmacy"),
      showWaiters: capabilities.waiters !== false,
      showChargeToRoom:
        Boolean(capabilities.charge_to_room) && hasModule("hotel"),
    };
  }, [profile, modules, hasModule]);
}
