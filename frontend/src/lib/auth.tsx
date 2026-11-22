/* Auth state: the logged-in user, login/register/logout, and the loading
 * flag pages use to wait for the session check before rendering. */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearTokens, getAccessToken, login, setTokens } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  // On first load, if a token exists, fetch the current user.
  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    apiFetch<User>("/auth/me")
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const doLogin = useCallback(
    async (email: string, password: string) => {
      const tokens = await login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await apiFetch<User>("/auth/me");
      setUser(me);
      router.push("/dashboard");
    },
    [router]
  );

  const doRegister = useCallback(
    async (email: string, password: string, fullName: string) => {
      // Register returns the user (not tokens), so log in right after.
      await apiFetch<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });
      await doLogin(email, password);
    },
    [doLogin]
  );

  return (
    <AuthContext.Provider
      value={{ user, loading, login: doLogin, register: doRegister, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
