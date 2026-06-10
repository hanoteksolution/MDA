export interface Company {
  id: string;
  name: string;
  legal_name: string;
  tax_id: string;
  email: string;
  phone: string;
  address: string;
  logo: string | null;
}

export interface BranchDetail {
  id: string;
  name: string;
  code: string;
  address: string;
  phone: string;
  email: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  is_active: boolean;
  role: { id: string; name: string; slug: string } | null;
  branch: { id: string; name: string; code: string } | null;
  last_login: string | null;
  date_joined: string;
}

export interface RoleDetail {
  id: string;
  name: string;
  slug: string;
  description: string;
  is_system: boolean;
  permission_count: number;
  permissions: { id: string; name: string; codename: string; module: string }[];
  created_at: string;
  updated_at: string;
}

export interface SystemSetting {
  id: string;
  key: string;
  value: Record<string, unknown>;
  category: string;
}
