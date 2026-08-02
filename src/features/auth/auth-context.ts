import { createContext, useContext } from "react";

export type Organization = {
  id: string;
  name: string;
  slug: string;
  kind: string;
  roles: string[];
};

export type CurrentUser = {
  id: string;
  email: string;
  display_name: string;
  email_verified: boolean;
  active_organization_id: string;
  organizations: Organization[];
};

export type AuthContextValue = {
  user: CurrentUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  activateOrganization: (organizationId: string) => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
