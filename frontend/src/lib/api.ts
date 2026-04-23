import { extractApiErrorMessage } from "./apiError";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(extractApiErrorMessage(payload) || `HTTP ${response.status}`);
  }

  return response.json();
}

// Sessions
export async function getSessions() {
  return fetchApi<import("@/types/session").SessionSummary[]>("/api/sessions");
}

export async function getSession(id: string) {
  return fetchApi<import("@/types/session").SessionDetail>(`/api/sessions/${id}`);
}

export async function createSession() {
  return fetchApi<import("@/types/session").SessionSummary>(
    "/api/sessions",
    { method: "POST" }
  );
}

export async function closeSession(id: string) {
  return fetchApi<{ ok: boolean }>(`/api/sessions/${id}`, { method: "DELETE" });
}

// Meta
export async function getMetaStatus() {
  return fetchApi<import("@/types/meta").EnvironmentStatus>("/api/meta/status");
}

// Chat
export async function chat(request: import("@/types/chat").ChatRequest) {
  return fetchApi<import("@/types/chat").ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function chatFollowUp(
  request: import("@/types/chat").ChatFollowUpRequest
) {
  return fetchApi<import("@/types/chat").ChatResponse>("/api/chat/follow-up", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function chatCompare(
  request: import("@/types/chat").ChatCompareRequest
) {
  return fetchApi<import("@/types/chat").ChatResponse>("/api/chat/compare", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// Profile
export async function getProfile() {
  return fetchApi<import("@/types/profile").UserProfile>("/api/profile");
}

export async function updateProfile(
  data: import("@/types/profile").UserProfileUpdate
) {
  return fetchApi<import("@/types/profile").UserProfile>("/api/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// Watchlist
export async function getWatchlist() {
  return fetchApi<import("@/types/watchlist").WatchItemRecord[]>("/api/watchlist");
}

export async function resolveWatchStock(
  data: import("@/types/watchlist").WatchStockResolveRequest
) {
  return fetchApi<import("@/types/watchlist").WatchStockCandidate>(
    "/api/watchlist/resolve",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function createWatchItem(
  data: import("@/types/watchlist").WatchItemCreate
) {
  return fetchApi<import("@/types/watchlist").WatchItemRecord>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateWatchItem(
  id: string,
  data: import("@/types/watchlist").WatchItemUpdate
) {
  return fetchApi<import("@/types/watchlist").WatchItemRecord>(
    `/api/watchlist/${id}`,
    { method: "PATCH", body: JSON.stringify(data) }
  );
}

export async function deleteWatchItem(id: string) {
  return fetchApi<void>(`/api/watchlist/${id}`, { method: "DELETE" });
}

// Templates
export async function getTemplates() {
  return fetchApi<import("@/types/template").TemplateRecord[]>("/api/templates");
}

export async function createTemplate(
  data: import("@/types/template").TemplateCreate
) {
  return fetchApi<import("@/types/template").TemplateRecord>("/api/templates", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTemplate(
  id: string,
  data: import("@/types/template").TemplateUpdate
) {
  return fetchApi<import("@/types/template").TemplateRecord>(
    `/api/templates/${id}`,
    { method: "PUT", body: JSON.stringify(data) }
  );
}

export async function deleteTemplate(id: string) {
  return fetchApi<void>(`/api/templates/${id}`, { method: "DELETE" });
}
