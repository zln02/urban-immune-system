/**
 * 경보·신호 도메인 타입 (Zod 스키마 기반).
 */

import { z } from "zod";

export const RiskLevel = z.enum(["safe", "caution", "warning", "alert"]);
export type RiskLevel = z.infer<typeof RiskLevel>;

export const LayerId = z.enum(["L1_pharmacy", "L2_sewage", "L3_search"]);
export type LayerId = z.infer<typeof LayerId>;

export const DistrictRiskSchema = z.object({
  district_code: z.string(),
  district_name: z.string(),
  risk_level: RiskLevel,
  confidence: z.number().min(0).max(1),
  updated_at: z.string().datetime(),
});
export type DistrictRisk = z.infer<typeof DistrictRiskSchema>;

export const AlertEventSchema = z.object({
  id: z.string().uuid(),
  district_code: z.string(),
  district_name: z.string(),
  risk_level: RiskLevel,
  layers_triggered: z.array(LayerId).min(1),
  message: z.string(),
  created_at: z.string().datetime(),
});
export type AlertEvent = z.infer<typeof AlertEventSchema>;

export const SignalPointSchema = z.object({
  timestamp: z.string().datetime(),
  layer: LayerId,
  value: z.number(),
  district_code: z.string().optional(),
});
export type SignalPoint = z.infer<typeof SignalPointSchema>;
