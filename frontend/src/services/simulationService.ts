import { request } from "./apiClient";
import type {
  City,
  InterventionSpec,
  InterventionType,
  SimulationRequest,
  SimulationResponse,
} from "../types";

export interface InterventionsMetadataResponse {
  interventions: Record<InterventionType, InterventionSpec>;
  assumptions: string[];
}

export const simulationService = {
  getInterventions(): Promise<InterventionsMetadataResponse> {
    return request<InterventionsMetadataResponse>("/api/interventions");
  },

  runSimulation(req: SimulationRequest): Promise<SimulationResponse> {
    return request<SimulationResponse>("/api/simulation/run", req);
  },

  getSimulationHistory(city: City | string): Promise<SimulationResponse[]> {
    return request<SimulationResponse[]>(
      `/api/simulation/results?city=${encodeURIComponent(city)}`,
    );
  },
};
