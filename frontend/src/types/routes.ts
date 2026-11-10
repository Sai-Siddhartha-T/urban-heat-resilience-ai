import type { City, MapLayer } from "./common";

export type PageSlug =
  | "overview"
  | "map"
  | "prediction"
  | "explain"
  | "risk"
  | "simulator"
  | "optimizer"
  | "assistant"
  | "reports"
  | "compare"
  | "environmental"
  | "heat";

export interface RouteState {
  page: PageSlug;
  city: City;
  zoneId?: string;
  layer: MapLayer;
}

export interface NavigationOptions {
  page?: string;
  city?: City;
  zoneId?: string;
  layer?: MapLayer;
}
