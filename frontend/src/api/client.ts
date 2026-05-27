import axios from "axios";

import type { PipelineOutput } from "../types/output";
import { useAuthStore } from "../stores/authStore";

export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export const api = axios.create({
  baseURL: "/api/v1",
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const path = window.location.pathname;
      if (!path.startsWith("/login") && !path.startsWith("/register")) {
        useAuthStore.getState().logout();
      }
    }
    return Promise.reject(error);
  },
);

/** True when the API responded 404 (e.g. run lost after server reload). */
export function isApiNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

/** User-visible message from a failed API call (upload, status, etc.). */
export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d)))
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
    if (error.response?.status === 401) {
      return "Authentication required. Please sign in again.";
    }
    if (error.response?.status === 409) {
      return typeof detail === "string" ? detail : "This email is already registered.";
    }
    if (error.response?.status === 500) {
      return "Server error — check that uvicorn is running and see the backend terminal for details.";
    }
    if (error.code === "ERR_NETWORK" || error.message.includes("Network Error")) {
      return "Cannot reach the API at /api — start the backend on port 8000.";
    }
    return error.message || `Request failed (${error.response?.status ?? "unknown"})`;
  }
  if (error instanceof Error) return error.message;
  return "Request failed";
}

export async function registerUser(payload: {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}) {
  const { data } = await api.post<AuthResponse>("/auth/register", payload);
  return data;
}

export async function loginUser(payload: { email: string; password: string }) {
  const { data } = await api.post<AuthResponse>("/auth/login", payload);
  return data;
}

export async function getCurrentUser() {
  const { data } = await api.get<AuthUser>("/auth/me");
  return data;
}

export async function fetchHealth() {
  const { data } = await api.get<{ status: string; server_boot_id: string }>("/health");
  return data;
}

export async function analyzeRfp(file: File): Promise<{ run_id: string; message?: string }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<{ run_id: string; message?: string }>("/rfp/analyze", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getRunStatus(runId: string) {
  const { data } = await api.get(`/rfp/${runId}/status`);
  return data as { run_id: string; status: string; progress: number; error?: string };
}

export async function getRunOutput(runId: string): Promise<PipelineOutput> {
  const { data } = await api.get(`/rfp/${runId}/output`);
  return data as PipelineOutput;
}

export type HistoryRun = {
  run_id: string;
  status: string;
  progress: number;
  error?: string | null;
  filename?: string | null;
  document_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  created_at?: string | null;
};

export async function listHistory() {
  const { data } = await api.get("/rfp/history");
  return data as { runs: HistoryRun[]; count?: number };
}

export async function deleteRun(runId: string) {
  const { data } = await api.delete(`/rfp/${runId}`);
  return data as { run_id: string; status: string };
}

export type ChatMessage = {
  role: string;
  content: string;
  timestamp?: string;
};

export async function getRunChat(runId: string) {
  const { data } = await api.get(`/rfp/${runId}/chat`);
  return data as {
    run_id: string;
    messages: ChatMessage[];
    clarification_started?: boolean;
  };
}

export async function postRunChat(runId: string, message: string) {
  const { data } = await api.post(`/rfp/${runId}/chat`, { message });
  return data as {
    assistant_message: string;
    suggested_questions?: string[];
    scope_updated?: boolean;
    messages: ChatMessage[];
  };
}

export async function resolveClarifications(
  runId: string,
  payload: {
    answers: Record<string, string>;
    suggested_inputs: Record<string, string>;
    additional_notes: string;
  },
  additionalFiles?: File[],
) {
  const form = new FormData();
  form.append("payload", JSON.stringify(payload));
  for (const file of additionalFiles ?? []) {
    form.append("additional_files", file);
  }
  const { data } = await api.post(`/rfp/${runId}/clarifications/resolve`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data as {
    run_id: string;
    resolved_items: number;
    final_sections: number;
    message?: string;
  };
}
