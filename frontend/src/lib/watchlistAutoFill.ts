"use client";

import { BUCKET_LABELS, MODE_LABELS } from "@/lib/utils";
import type { JsonValue, ChatMode, WatchBucket } from "@/types/common";
import type { WatchStockCandidate } from "@/types/watchlist";

type RowRecord = Record<string, JsonValue>;

function dedupeTags(tags: Array<string | null | undefined>): string[] {
  const unique: string[] = [];
  const seen = new Set<string>();

  for (const rawTag of tags) {
    const tag = String(rawTag || "").trim();
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    unique.push(tag);
  }

  return unique.slice(0, 8);
}

function splitTagParts(value: string | null | undefined, limit: number): string[] {
  const text = String(value || "").trim();
  if (!text) return [];
  return text
    .split(/[、,，/]/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, limit);
}

function jsonToText(value: JsonValue | undefined): string | null {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) {
    const parts = value
      .map((entry) => String(entry || "").trim())
      .filter(Boolean);
    return parts.length ? parts.join("、") : null;
  }
  return String(value).trim() || null;
}

function findRowValue(row: RowRecord | null | undefined, keys: string[]): string | null {
  if (!row) return null;

  for (const key of keys) {
    const exact = jsonToText(row[key]);
    if (exact) return exact;
  }

  const loweredKeys = keys.map((key) => key.toLowerCase());
  for (const [rawKey, value] of Object.entries(row)) {
    const lowered = rawKey.toLowerCase();
    if (loweredKeys.some((key) => lowered.includes(key))) {
      const matched = jsonToText(value);
      if (matched) return matched;
    }
  }

  return null;
}

function extractFirstSentence(value: string | null | undefined): string | null {
  const text = String(value || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return null;

  const sentence = text.split(/[。！？；;\n]/)[0]?.trim() || text;
  if (!sentence) return null;
  if (sentence.length <= 88) return sentence;
  return `${sentence.slice(0, 88).trim()}...`;
}

function resolveModeTag(mode: ChatMode | null | undefined, bucket: WatchBucket | null | undefined): string | null {
  if (mode === "short_term" || mode === "swing" || mode === "mid_term_value" || mode === "generic_data_query") {
    return MODE_LABELS[mode];
  }
  if (bucket) return BUCKET_LABELS[bucket];
  return null;
}

export function mergeWatchTags(autoTags: string[], manualTags: string[]): string[] {
  return dedupeTags([...autoTags, ...manualTags]);
}

export function buildAutoWatchTags(options: {
  candidate?: Pick<WatchStockCandidate, "industry" | "concepts"> | null;
  row?: RowRecord | null;
  mode?: ChatMode | null;
  bucket?: WatchBucket | null;
}): string[] {
  const rowIndustry = findRowValue(options.row, ["所属同花顺行业", "所属行业", "行业"]);
  const rowConcepts = findRowValue(options.row, ["所属概念", "概念", "题材"]);
  const industryTags = splitTagParts(options.candidate?.industry || rowIndustry, 2);
  const conceptTags = [
    ...(options.candidate?.concepts || []).slice(0, 3),
    ...splitTagParts(rowConcepts, 3),
  ];
  const modeTag = resolveModeTag(options.mode, options.bucket);

  return dedupeTags([...industryTags, ...conceptTags, modeTag]);
}

export function buildAutoWatchNote(options: {
  name: string;
  row?: RowRecord | null;
  summary?: string | null;
  judgements?: string[] | null;
}): string | null {
  const rowSpecific = extractFirstSentence(
    findRowValue(options.row, ["核心逻辑", "基本面", "风险点"])
  );
  if (rowSpecific) return rowSpecific;

  const judgement = extractFirstSentence(options.judgements?.[0] || null);
  if (judgement) {
    return judgement.includes(options.name) ? judgement : `${options.name}：${judgement}`;
  }

  const summary = extractFirstSentence(options.summary || null);
  if (!summary) return null;
  return summary.includes(options.name) ? summary : `${options.name}：${summary}`;
}
