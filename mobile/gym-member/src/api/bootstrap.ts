import { apiRequest } from "./client";

export interface MobileNavScreen {
  id: string;
  label: string;
  route: string;
  workspace: string;
  module: string;
  sort_order: number;
}

export interface MobileNavWorkspace {
  id: string;
  label: string;
  module: string;
  audience: string;
  screens: MobileNavScreen[];
}

export interface MobileNav {
  enabled_modules: string[];
  workspaces: MobileNavWorkspace[];
  screens: MobileNavScreen[];
}

export interface MobileBootstrap {
  user?: {
    username?: string;
    enabled_modules?: string[];
  };
  enabled_modules?: string[];
  mobile_nav?: MobileNav;
  gym_member?: {
    member?: {
      id: string;
      membership_number: string;
      full_name: string;
      status: string;
    };
  } | null;
  entitlements?: {
    enabled_modules?: string[];
    can_write?: boolean;
    phase?: string;
  } | null;
}

export function fetchBootstrap() {
  return apiRequest<MobileBootstrap>("/mobile/bootstrap/?audience=member");
}
