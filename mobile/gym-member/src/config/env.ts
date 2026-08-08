import Constants from "expo-constants";

/** Override in app dev settings or `.env` via expo extra. */
export const API_BASE =
  (Constants.expoConfig?.extra?.apiBase as string | undefined) ??
  "http://127.0.0.1:8000/api/v1";

export const DEFAULT_TENANT_SLUG =
  (Constants.expoConfig?.extra?.tenantSlug as string | undefined) ?? "";
