export interface WeatherSeriesPoint {
  date: string; // ISO date "YYYY-MM-DD"
  air_temperature_c: number | null;
  relative_humidity_pct: number | null;
  hours_with_temperature?: number;
  rainfall_mm?: number | null;
  wind_speed_m_s?: number | null;
  solar_radiation_mj_m2_day?: number | null;
}

export interface WeatherSeries {
  id?: string;
  source: string;
  latitude: number;
  longitude: number;
  synthetic: boolean;
  variable: string;
  points: WeatherSeriesPoint[];
}

export interface WeatherDataResponse {
  series: WeatherSeries[];
  note?: string;
}

// Alias for backwards compatibility if referenced
export type WeatherSeriesResponse = WeatherDataResponse;
