import type { ChatMode, GptReasoningPolicy } from "./common";

export interface UserProfile {
  capital: number | null;
  position_limit_pct: number | null;
  max_drawdown_pct: number | null;
  holding_horizon: string | null;
  risk_style: string | null;
  preferred_sectors: string[];
  default_mode: ChatMode | null;
  default_result_size: number;
  gpt_enhancement_enabled: boolean;
  gpt_reasoning_policy: GptReasoningPolicy;
}

export interface UserProfileUpdate {
  capital?: number | null;
  position_limit_pct?: number | null;
  max_drawdown_pct?: number | null;
  holding_horizon?: string | null;
  risk_style?: string | null;
  preferred_sectors?: string[] | null;
  default_mode?: ChatMode | null;
  default_result_size?: number | null;
  gpt_enhancement_enabled?: boolean | null;
  gpt_reasoning_policy?: GptReasoningPolicy | null;
}
