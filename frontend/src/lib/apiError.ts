import type { JsonValue } from "@/types";

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function firstValidationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null;

  for (const item of detail) {
    if (typeof item === "string" && item.trim()) {
      return item.trim();
    }
    const issue = asRecord(item);
    if (!issue) continue;
    const msg = typeof issue.msg === "string" ? issue.msg.trim() : "";
    const loc = Array.isArray(issue.loc)
      ? issue.loc
          .filter((part): part is string | number => typeof part === "string" || typeof part === "number")
          .map(String)
          .filter((part) => part !== "body")
          .join(".")
      : "";
    if (msg && loc) return `${loc}: ${msg}`;
    if (msg) return msg;
  }

  return null;
}

export function extractApiErrorMessage(payload: JsonValue | Record<string, unknown> | null | undefined): string | null {
  const record = asRecord(payload);
  if (!record) return null;

  const userVisibleError = asRecord(record.user_visible_error);
  if (typeof userVisibleError?.message === "string" && userVisibleError.message.trim()) {
    return userVisibleError.message.trim();
  }

  if (typeof record.detail === "string" && record.detail.trim()) {
    return record.detail.trim();
  }

  const validationMessage = firstValidationMessage(record.detail);
  if (validationMessage) return validationMessage;

  if (typeof record.error === "string" && record.error.trim()) {
    return record.error.trim();
  }

  return null;
}
