import type { ApiResponse, AuthTokens, User } from "@/types/models";
import type { Company } from "@/types/models/admin";
import { apiRequest } from "./http";

export const setupApi = {
  status: () =>
    apiRequest<ApiResponse<{ needs_setup: boolean }>>("/setup/status/"),

  complete: (data: {
    company: Partial<Company>;
    user: { username: string; email: string; password: string; first_name?: string; last_name?: string };
    branch?: { name?: string; code?: string };
  }) =>
    apiRequest<
      ApiResponse<
        AuthTokens & {
          user: User;
          company: Company;
          branch: { id: string; name: string; code: string };
        }
      >
    >("/setup/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
