import React, { useState, useEffect } from "react";
import { Database, Search, Menu } from "lucide-react";
import type { City, MapLayer, ZoneFeature } from "../../types";
import { SyntheticWarningBadge } from "../common/SyntheticWarningBadge";
import { CommandBar } from "./CommandBar";

export interface TopbarProps {
  city: City | string;
  onCityChange: (city: City) => void;
  onOpenData: () => void;
  databaseStatus?: string;
  className?: string;
  isSynthetic?: boolean;
  onNavigate?: (page: string) => void;
  onSelectZone?: (zoneId: string) => void;
  onSelectLayer?: (layer: MapLayer) => void;
  zones?: ZoneFeature[];
  onToggleSidebar?: () => void;
  isSidebarCollapsed?: boolean;
}

const CITIES: City[] = ["Ahmedabad", "Delhi", "Hyderabad"];

export function Topbar({
  city,
  onCityChange,
  onOpenData,
  databaseStatus = "sqlite",
  className = "",
  isSynthetic = false,
  onNavigate,
  onSelectZone,
  onSelectLayer,
  zones,
  onToggleSidebar,
}: TopbarProps) {
  const [commandOpen, setCommandOpen] = useState(false);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <header className={`topbar ${className}`.trim()}>
        <div className="topbar-left">
          {onToggleSidebar && (
            <button
              type="button"
              className="topbar-menu-btn"
              onClick={onToggleSidebar}
              title="Toggle sidebar navigation"
              aria-label="Toggle navigation menu"
            >
              <Menu size={18} />
            </button>
          )}

          {/* Quick city switcher */}
          <div className="city-picker" role="tablist" aria-label="City Selector">
            {CITIES.map((c) => (
              <button
                key={c}
                type="button"
                className={`city-tab ${city === c ? "active" : ""}`}
                onClick={() => onCityChange(c)}
                role="tab"
                aria-selected={city === c}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Center Omni-Search Command Trigger */}
        <div className="topbar-center">
          <button
            type="button"
            className="command-trigger-btn"
            onClick={() => setCommandOpen(true)}
            title="Omni-search views, cities, zones, layers (Ctrl+K)"
          >
            <Search size={14} className="command-trigger-icon" />
            <span className="command-trigger-text">
              Quick search or jump to view…
            </span>
            <kbd className="command-trigger-kbd">⌘K / Ctrl+K</kbd>
          </button>
        </div>

        {/* Right Actions */}
        <div className="topbar-actions">
          {isSynthetic && <SyntheticWarningBadge isSynthetic={isSynthetic} />}

          <button
            type="button"
            className="top-btn"
            onClick={onOpenData}
            title="Open Data Ingestion and Catalog"
          >
            <Database size={14} />
            <span>Data sources</span>
          </button>

          <span
            className={`status-pill ${
              databaseStatus.toLowerCase().includes("sqlite") ||
              databaseStatus.toLowerCase().includes("postgis") ||
              databaseStatus.toLowerCase().includes("ok")
                ? "ok"
                : "warn"
            }`}
            title={`Database backend: ${databaseStatus}`}
          >
            <span className="dot" />
            {databaseStatus || "offline"}
          </span>
        </div>
      </header>

      {/* Omni-Search Command Palette */}
      <CommandBar
        isOpen={commandOpen}
        onClose={() => setCommandOpen(false)}
        city={city as City}
        onCityChange={onCityChange}
        onNavigate={onNavigate || (() => {})}
        onSelectZone={onSelectZone}
        onSelectLayer={onSelectLayer}
        zones={zones}
      />
    </>
  );
}
