import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
};

type AuthState = {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  serverBootId: string | null;
  setSession: (token: string, user: AuthUser, serverBootId: string) => void;
  setServerBootId: (serverBootId: string) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      serverBootId: null,
      setSession: (token, user, serverBootId) =>
        set({ token, user, isAuthenticated: true, serverBootId }),
      setServerBootId: (serverBootId) => set({ serverBootId }),
      logout: () =>
        set({ token: null, user: null, isAuthenticated: false, serverBootId: null }),
    }),
    {
      name: "presales-auth",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        serverBootId: state.serverBootId,
      }),
    },
  ),
);
