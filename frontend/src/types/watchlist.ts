import type { WatchBucket } from "./common";

export interface WatchItemCreate {
  query?: string | null;
  symbol?: string | null;
  name?: string | null;
  bucket: WatchBucket;
  tags: string[];
  note?: string | null;
  source_session_id?: string | null;
}

export interface WatchItemUpdate {
  bucket?: WatchBucket | null;
  tags?: string[] | null;
  note?: string | null;
}

export interface WatchItemRecord {
  id: string;
  symbol: string;
  name: string;
  bucket: WatchBucket;
  tags: string[];
  note?: string | null;
  source_session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WatchStockResolveRequest {
  query: string;
}

export interface WatchStockCandidate {
  symbol: string;
  name: string;
  latest_price?: number | null;
  change_pct?: number | null;
  industry?: string | null;
  concepts: string[];
  source_query: string;
}
