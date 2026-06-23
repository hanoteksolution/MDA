import type { ApiResponse, AuthTokens, DashboardKPIs, User } from "@/types/models";
import { apiRequest } from "./http";

export interface DesktopUserStatus {
  exists: boolean;
  provisioned: boolean;
}

class ApiClient {
  async login(username: string, password: string) {
    return apiRequest<ApiResponse<AuthTokens & { user: User }>>("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  async desktopUserStatus(username: string) {
    return apiRequest<ApiResponse<DesktopUserStatus>>(
      `/auth/desktop-status/?username=${encodeURIComponent(username)}`
    );
  }

  async desktopProvision(username: string, password: string, cloudAccessToken: string) {
    return apiRequest<ApiResponse<AuthTokens & { user: User }>>("/auth/desktop-provision/", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
        cloud_access_token: cloudAccessToken,
      }),
    });
  }

  async logout(refresh: string) {
    return apiRequest<ApiResponse<null>>("/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh }),
    });
  }

  async getMe() {
    return apiRequest<ApiResponse<User>>("/auth/me/");
  }

  async getDashboardKPIs(period = "today") {
    return apiRequest<ApiResponse<DashboardKPIs>>(`/dashboard/kpis/?period=${period}`);
  }
}

export const api = new ApiClient();
