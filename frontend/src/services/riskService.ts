import { request } from "./apiClient";
import type { RiskAnalysisResponse, RiskRequest } from "../types";

export const riskService = {
  analyzeRisk(req: RiskRequest): Promise<RiskAnalysisResponse> {
    return request<RiskAnalysisResponse>("/api/risk/analyze", req);
  },
};
