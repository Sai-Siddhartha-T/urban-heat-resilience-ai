import { useState, useEffect, useCallback } from "react";
import type { City, MapLayer, NavigationOptions, PageSlug, RouteState } from "../types";
import { PAGE_MAP, DEFAULT_ROUTE } from "../lib/constants";

export function useHashRouter() {
  const parseHash = (): RouteState => {
    if (typeof window === "undefined") return DEFAULT_ROUTE;
    const raw = window.location.hash.replace(/^#\/?/, "");
    const [pathPart, queryPart] = raw.split("?");
    const slug = (pathPart || "overview").toLowerCase() as PageSlug;
    const pageDef = PAGE_MAP[slug] || PAGE_MAP[pathPart] || PAGE_MAP.overview;
    const params = new URLSearchParams(queryPart || "");
    const city = (params.get("city") || "Ahmedabad") as City;
    const zoneId = params.get("zone") || "";
    const layer = (params.get("layer") || "predicted_suhii") as MapLayer;
    return {
      page: pageDef.slug,
      city,
      zoneId,
      layer,
    };
  };

  const [route, setRoute] = useState<RouteState>(parseHash);

  useEffect(() => {
    const handleHashChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback(
    (target: string | NavigationOptions, params?: Record<string, string>) => {
      let next: RouteState;
      if (typeof target === "string") {
        const pageDef =
          PAGE_MAP[target] || PAGE_MAP[target.toLowerCase()] || PAGE_MAP.overview;
        next = {
          ...route,
          page: pageDef.slug,
          zoneId: params?.zone ?? route.zoneId,
          layer: (params?.layer as MapLayer) ?? route.layer,
        };
      } else {
        const pageDef = target.page
          ? PAGE_MAP[target.page] ||
            PAGE_MAP[target.page.toLowerCase()] ||
            PAGE_MAP.overview
          : null;
        next = {
          page: pageDef ? pageDef.slug : route.page,
          city: target.city ?? route.city,
          zoneId: target.zoneId ?? route.zoneId,
          layer: target.layer ?? route.layer,
        };
      }

      const query = new URLSearchParams();
      if (next.city) query.set("city", next.city);
      if (next.zoneId) query.set("zone", next.zoneId);
      if (next.layer && next.layer !== "predicted_suhii") {
        query.set("layer", next.layer);
      }

      const queryString = query.toString();
      const hash = `#/${next.page}${queryString ? `?${queryString}` : ""}`;
      if (window.location.hash !== hash) {
        window.location.hash = hash;
      }
      setRoute(next);
    },
    [route],
  );

  const setCity = useCallback(
    (city: City) => {
      navigate({ city, zoneId: "" });
    },
    [navigate],
  );

  const setLayer = useCallback(
    (layer: MapLayer | string) => {
      navigate({ layer: layer as MapLayer });
    },
    [navigate],
  );

  return {
    route,
    page: route.page,
    city: route.city,
    zoneId: route.zoneId,
    layer: route.layer,
    navigate,
    setCity,
    setLayer,
  };
}
