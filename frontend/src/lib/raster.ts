export const RASTER_LAYERS: string[] = [
  "predicted_suhii",
  "ndvi",
  "building_density",
  "population_density",
  "ndbi",
  "ndwi",
  "ndbai",
  "lst",
];

export function isRasterLayer(layerName: string): boolean {
  return (
    RASTER_LAYERS.includes(layerName) ||
    layerName.startsWith("raster_") ||
    layerName.startsWith("sentinel_")
  );
}
