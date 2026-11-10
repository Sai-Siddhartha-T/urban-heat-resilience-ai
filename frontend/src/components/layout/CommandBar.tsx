import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Search,
  Compass,
  Map as MapIcon,
  Cpu,
  Activity,
  AlertTriangle,
  HelpCircle,
  Sliders,
  Sparkles,
  Bot,
  FileText,
  MapPin,
  Layers,
  Building,
  Scale,
  X,
} from "lucide-react";
import type { City, MapLayer, ZoneFeature } from "../../types";
import { CITIES, PAGES } from "../../lib/constants";

export interface CommandBarProps {
  isOpen: boolean;
  onClose: () => void;
  city: City;
  onCityChange: (c: City) => void;
  onNavigate: (page: string) => void;
  onSelectZone?: (zoneId: string) => void;
  onSelectLayer?: (layer: MapLayer) => void;
  zones?: ZoneFeature[];
}

interface CommandItem {
  id: string;
  category: "Views" | "Cities" | "Layers" | "Zones";
  title: string;
  subtitle?: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  action: () => void;
}

export function CommandBar({
  isOpen,
  onClose,
  city,
  onCityChange,
  onNavigate,
  onSelectZone,
  onSelectLayer,
  zones = [],
}: CommandBarProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const items = useMemo<CommandItem[]>(() => {
    const list: CommandItem[] = [];

    // 1. Canonical Views
    PAGES.forEach((p) => {
      list.push({
        id: `view-${p.slug}`,
        category: "Views",
        title: p.title,
        subtitle: `Jump to ${p.title} view`,
        icon: p.icon,
        action: () => {
          onNavigate(p.title);
          onClose();
        },
      });
    });

    list.push({
      id: "view-compare",
      category: "Views",
      title: "Zone comparison",
      subtitle: "Multi-ward comparison matrix",
      icon: Scale,
      action: () => {
        onNavigate("Zone comparison");
        onClose();
      },
    });

    // 2. Cities
    (Object.keys(CITIES) as City[]).forEach((c) => {
      list.push({
        id: `city-${c}`,
        category: "Cities",
        title: c,
        subtitle: c === city ? "Currently selected target city" : `Switch target city to ${c}`,
        icon: Building,
        action: () => {
          onCityChange(c);
          onClose();
        },
      });
    });

    // 3. Map Layers
    const layerDefs: Array<{ id: MapLayer; label: string; desc: string }> = [
      { id: "predicted_suhii", label: "Surface Heat · SUHII", desc: "Predicted SUHII anomaly in °C" },
      { id: "lst", label: "Land Surface Temperature · LST", desc: "Landsat / MODIS surface temp in °C" },
      { id: "risk_score", label: "Heat Risk Index", desc: "Composite hazard-exposure-vulnerability (0-100)" },
      { id: "ndvi", label: "Vegetation Index · NDVI", desc: "Sentinel-2 spectral index [-1, 1]" },
      { id: "building_density", label: "Built-up Density", desc: "Building footprint coverage percentage" },
      { id: "population_density", label: "Population Density", desc: "WorldPop / GHSL exposure per km²" },
      { id: "air_quality", label: "Air Quality Stations", desc: "OpenAQ / CPCB telemetry stations" },
      { id: "weather_stations", label: "Weather Telemetry", desc: "Open-Meteo observation stations" },
      { id: "groundwater", label: "Groundwater Wells", desc: "CGWB depth to water table in mbgl" },
    ];

    layerDefs.forEach((l) => {
      list.push({
        id: `layer-${l.id}`,
        category: "Layers",
        title: l.label,
        subtitle: l.desc,
        icon: Layers,
        action: () => {
          onSelectLayer?.(l.id);
          onNavigate("map");
          onClose();
        },
      });
    });

    // 4. City Zones (top 20 or matching)
    if (zones && zones.length > 0) {
      zones.slice(0, 20).forEach((z) => {
        list.push({
          id: `zone-${z.properties.id}`,
          category: "Zones",
          title: z.properties.name,
          subtitle: `${z.properties.id} · SUHII: ${Number(z.properties.predicted_suhii).toFixed(1)}°C · Risk: ${z.properties.risk_level}`,
          icon: MapPin,
          action: () => {
            onSelectZone?.(z.properties.id);
            onNavigate("map");
            onClose();
          },
        });
      });
    }

    return list;
  }, [city, zones, onCityChange, onNavigate, onSelectZone, onSelectLayer, onClose]);

  // Filter items by query
  const filteredItems = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q)) ||
        item.category.toLowerCase().includes(q),
    );
  }, [items, query]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filteredItems.length || 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + (filteredItems.length || 1)) % (filteredItems.length || 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredItems, selectedIndex, onClose]);

  // Scroll active item into view
  useEffect(() => {
    if (listRef.current) {
      const activeEl = listRef.current.querySelector(".command-item.active") as HTMLElement;
      if (activeEl) {
        activeEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="command-palette-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="command-palette"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="command-input-row">
          <Search size={18} className="command-search-icon" />
          <input
            ref={inputRef}
            type="text"
            className="command-input"
            placeholder="Type a command, city, zone, layer, or view… (e.g. 'Delhi', 'NDVI', 'Risk')"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
          />
          <button type="button" className="command-close-btn" onClick={onClose} title="Close command palette (Esc)">
            <X size={16} />
          </button>
        </div>

        <div className="command-list" ref={listRef}>
          {filteredItems.length === 0 ? (
            <div className="command-empty">
              <Search size={24} />
              <p>No results found for “{query}”</p>
              <span>Try searching for views like “Overview”, cities like “Ahmedabad”, or layers like “NDVI”</span>
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  className={`command-item ${isSelected ? "active" : ""}`}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className="command-item-icon">
                    <Icon size={16} />
                  </div>
                  <div className="command-item-content">
                    <div className="command-item-title">
                      <span>{item.title}</span>
                      <span className="command-item-category">{item.category}</span>
                    </div>
                    {item.subtitle && <p className="command-item-subtitle">{item.subtitle}</p>}
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="command-palette-footer">
          <div className="command-hints">
            <span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Select</span>
            <span><kbd>Esc</kbd> Close</span>
          </div>
          <span className="command-brand">Heatwise Command Platform</span>
        </div>
      </div>
    </div>
  );
}
