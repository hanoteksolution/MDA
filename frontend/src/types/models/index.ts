export interface Role {
  id: string;
  name: string;
  slug: string;
}

export interface Branch {
  id: string;
  name: string;
  code: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role | null;
  branch: Branch | null;
  permissions: string[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface DashboardKPIs {
  total_sales: number;
  revenue: number;
  cash_collected: number;
  profit: number;
  expenses: number;
  inventory_value: number;
  period: string;
}
