import { describe, it, expect } from "vitest";
import { computeWeatherExtremes } from "../lib/utils";
import type { WeatherSeriesPoint } from "../types";

describe("Weather Series Data Processing", () => {
  const samplePoints: WeatherSeriesPoint[] = [
    { date: "2024-05-01", air_temperature_c: 38.2, relative_humidity_pct: 32.0, hours_with_temperature: 24 },
    { date: "2024-05-02", air_temperature_c: 41.5, relative_humidity_pct: 28.5, hours_with_temperature: 24 },
    { date: "2024-05-03", air_temperature_c: 39.8, relative_humidity_pct: 30.0, hours_with_temperature: 24 },
    { date: "2024-05-04", air_temperature_c: 37.0, relative_humidity_pct: null, hours_with_temperature: 24 },
  ];

  it("computes accurate temperature extremes across sampled dates", () => {
    const extremes = computeWeatherExtremes(samplePoints);
    expect(extremes.maxTemp).toBe(41.5);
    expect(extremes.minTemp).toBe(37.0);
    expect(extremes.meanTemp).toBe(39.1);
  });

  it("computes mean humidity while ignoring null records", () => {
    const extremes = computeWeatherExtremes(samplePoints);
    // (32.0 + 28.5 + 30.0) / 3 = 30.166... -> 30.2
    expect(extremes.meanHumidity).toBe(30.2);
  });

  it("handles empty weather series gracefully without throwing", () => {
    const extremes = computeWeatherExtremes([]);
    expect(extremes.maxTemp).toBeNull();
    expect(extremes.meanHumidity).toBeNull();
  });
});
