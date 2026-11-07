export async function api<T = any>(path: string, body?: unknown): Promise<T> {
  const token = sessionStorage.getItem("heatwise-token");
  const response = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Could not reach the server." }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}
export async function download(url: string, name: string) {
  const token = sessionStorage.getItem("heatwise-token");
  const r = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!r.ok) throw new Error("Download failed");
  const href = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = href;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}
export const fmt = (n: number, d = 1) =>
  Number(n).toLocaleString("en-IN", {
    maximumFractionDigits: d,
    minimumFractionDigits: d,
  });
export const label = (s: string) =>
  ({
    ndvi: "Vegetation index",
    ndbi: "Built-up index",
    ndwi: "Water index",
    ndbai: "Bare-soil index",
    building_density: "Building density",
    population_density: "Population density",
    air_temperature: "Air temperature",
    humidity: "Relative humidity",
    rainfall: "Rainfall",
    solar_radiation: "Solar radiation",
    soil_moisture: "Soil moisture",
    land_cover: "Land cover",
  })[s] || s.replaceAll("_", " ");
