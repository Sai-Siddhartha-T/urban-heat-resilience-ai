import { request } from "./apiClient";
import type { City, WeatherDataResponse } from "../types";

export const weatherService = {
  getWeatherSeries(city?: City | string): Promise<WeatherDataResponse> {
    return request<WeatherDataResponse>(`/api/data/series${city ? `?city=${encodeURIComponent(city)}` : ""}`);
  },
};
