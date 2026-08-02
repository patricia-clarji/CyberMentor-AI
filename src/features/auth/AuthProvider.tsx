import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { apiFetch, ApiError } from "../../lib/api-client";
import { AuthContext, type CurrentUser } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiFetch<CurrentUser>("/api/v1/auth/me"),
    retry: (count, error) =>
      error instanceof ApiError && error.status >= 500 && count < 2,
    staleTime: 30_000,
  });
  const user =
    query.error instanceof ApiError && query.error.status === 401
      ? null
      : (query.data ?? null);
  return (
    <AuthContext.Provider
      value={{
        user,
        loading: query.isLoading,
        refresh: async () => {
          await queryClient.invalidateQueries({ queryKey: ["current-user"] });
        },
        logout: async () => {
          await apiFetch("/api/v1/auth/logout", {
            method: "POST",
          });
          queryClient.setQueryData(["current-user"], null);
        },
        activateOrganization: async (organizationId: string) => {
          await apiFetch(`/api/v1/organizations/${organizationId}/activate`, {
            method: "POST",
          });
          queryClient.removeQueries({
            predicate: (item) => item.queryKey[0] !== "current-user",
          });
          await queryClient.invalidateQueries({ queryKey: ["current-user"] });
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
