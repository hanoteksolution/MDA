import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  read_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface NotificationListResult {
  results: NotificationItem[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const notificationsApi = {
  list: (params: { is_read?: boolean; type?: string; page?: number; page_size?: number } = {}) =>
    apiRequest<ApiResponse<NotificationListResult>>(`/notifications/${qs(params)}`),

  unreadCount: () =>
    apiRequest<ApiResponse<{ count: number }>>("/notifications/unread-count/"),

  markRead: (id: string) =>
    apiRequest<ApiResponse<NotificationItem>>(`/notifications/${id}/read/`, {
      method: "POST",
    }),

  markAllRead: () =>
    apiRequest<ApiResponse<{ updated: number }>>("/notifications/read-all/", {
      method: "POST",
    }),
};
