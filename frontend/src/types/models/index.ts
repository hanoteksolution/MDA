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
  enabled_modules?: string[];
  module_features?: Record<string, Record<string, boolean>>;
  tenant_id?: string | null;
  tenant_name?: string | null;
  shop_slug?: string | null;
  business_type_code?: string | null;
  business_type_name?: string | null;
  is_platform_admin?: boolean;
  is_superuser?: boolean;
  is_super_admin?: boolean;
  managed_shop_group?: { id: string; name: string; slug: string } | null;
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
