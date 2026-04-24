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

export async function getWatchMonitorStatus() {
  return fetchApi<import("@/types/watchlist").WatchMonitorStatus>("/api/monitor/status");
}

export async function getWatchMonitorRules(itemId?: string) {
  const suffix = itemId ? `?item_id=${encodeURIComponent(itemId)}` : "";
  return fetchApi<import("@/types/watchlist").MonitorRuleRecord[]>(`/api/monitor/rules${suffix}`);
}

export async function createWatchMonitorRule(
  data: import("@/types/watchlist").MonitorRuleCreate
) {
  return fetchApi<import("@/types/watchlist").MonitorRuleRecord>("/api/monitor/rules", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateWatchMonitorRule(
  id: string,
  data: import("@/types/watchlist").MonitorRuleUpdate
) {
  return fetchApi<import("@/types/watchlist").MonitorRuleRecord>(`/api/monitor/rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteWatchMonitorRule(id: string) {
  return fetchApi<{ ok: boolean }>(`/api/monitor/rules/${id}`, {
    method: "DELETE",
  });
}

export async function getWatchMonitorEvents(limit = 20) {
  return fetchApi<import("@/types/watchlist").WatchMonitorEvent[]>(
    `/api/monitor/events?limit=${limit}`
  );
}

export async function triggerWatchMonitorScan() {
  return fetchApi<import("@/types/watchlist").WatchMonitorScanResponse>("/api/monitor/scan", {
    method: "POST",
  });
}

export async function getMonitorNotificationChannels() {
  return fetchApi<import("@/types/notification").MonitorNotificationChannelRecord[]>(
    "/api/monitor/notifications/channels"
  );
}

export async function createMonitorNotificationChannel(
  data: import("@/types/notification").MonitorNotificationChannelCreate
) {
  return fetchApi<import("@/types/notification").MonitorNotificationChannelRecord>(
    "/api/monitor/notifications/channels",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function updateMonitorNotificationChannel(
  id: string,
  data: import("@/types/notification").MonitorNotificationChannelUpdate
) {
  return fetchApi<import("@/types/notification").MonitorNotificationChannelRecord>(
    `/api/monitor/notifications/channels/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteMonitorNotificationChannel(id: string) {
  return fetchApi<{ ok: boolean }>(`/api/monitor/notifications/channels/${id}`, {
    method: "DELETE",
  });
}

export async function testMonitorNotificationChannel(id: string) {
  return fetchApi<import("@/types/notification").MonitorNotificationDeliveryRecord>(
    `/api/monitor/notifications/channels/${id}/test`,
    {
      method: "POST",
    }
  );
}

export async function getMonitorNotificationSettings() {
  return fetchApi<import("@/types/notification").MonitorNotificationSettings>(
    "/api/monitor/notifications/settings"
  );
}

export async function updateMonitorNotificationSettings(
  data: import("@/types/notification").MonitorNotificationSettingsUpdate
) {
  return fetchApi<import("@/types/notification").MonitorNotificationSettings>(
    "/api/monitor/notifications/settings",
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

export async function getMonitorNotificationDeliveries(limit = 20) {
  return fetchApi<import("@/types/notification").MonitorNotificationDeliveryRecord[]>(
    `/api/monitor/notifications/deliveries?limit=${limit}`
  );
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

// Portfolio
export async function getPortfolioSummary() {
  return fetchApi<import("@/types/portfolio").PortfolioSummary>("/api/portfolio/summary");
}

export async function getPortfolioAccounts() {
  return fetchApi<import("@/types/portfolio").PortfolioAccountRecord[]>("/api/portfolio/accounts");
}

export async function createPortfolioAccount(
  data: import("@/types/portfolio").PortfolioAccountCreate
) {
  return fetchApi<import("@/types/portfolio").PortfolioAccountRecord>("/api/portfolio/accounts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePortfolioAccount(
  id: string,
  data: import("@/types/portfolio").PortfolioAccountUpdate
) {
  return fetchApi<import("@/types/portfolio").PortfolioAccountRecord>(`/api/portfolio/accounts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deletePortfolioAccount(id: string) {
  return fetchApi<{ ok: boolean }>(`/api/portfolio/accounts/${id}`, { method: "DELETE" });
}

export async function createPortfolioPosition(
  data: import("@/types/portfolio").PortfolioPositionCreate
) {
  return fetchApi<import("@/types/portfolio").PortfolioPositionRecord>("/api/portfolio/positions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePortfolioPosition(
  id: string,
  data: import("@/types/portfolio").PortfolioPositionUpdate
) {
  return fetchApi<import("@/types/portfolio").PortfolioPositionRecord>(`/api/portfolio/positions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deletePortfolioPosition(id: string) {
  return fetchApi<{ ok: boolean }>(`/api/portfolio/positions/${id}`, { method: "DELETE" });
}

export async function importPortfolioScreenshot(
  data: import("@/types/portfolio").PortfolioScreenshotImportRequest
) {
  return fetchApi<import("@/types/portfolio").PortfolioScreenshotImportResponse>(
    "/api/portfolio/import-screenshot",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}
