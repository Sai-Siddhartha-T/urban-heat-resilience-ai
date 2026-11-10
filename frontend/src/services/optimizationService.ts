import { request } from "./apiClient";
import type {
  City,
  OptimizationRequest,
  OptimizationResponse,
} from "../types";

export const optimizationService = {
  runOptimization(req: OptimizationRequest): Promise<OptimizationResponse> {
    // Whitelist the physical-only contract so stale clients cannot submit
    // retired financial fields at runtime.
    return request<OptimizationResponse>("/api/optimization/run", {
      city: req.city,
      zone_ids: req.zone_ids,
      water_limit: req.water_limit,
      max_vegetation_pct: req.max_vegetation_pct,
      land_limit_pct: req.land_limit_pct,
      min_cooling: req.min_cooling,
    });
  },

  getOptimizationHistory(city: City | string): Promise<OptimizationResponse[]> {
    return request<OptimizationResponse[]>(
      `/api/optimization/results?city=${encodeURIComponent(city)}`,
    );
  },
};
