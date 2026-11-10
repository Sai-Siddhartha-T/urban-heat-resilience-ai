import React from "react";
import {
  Sparkles,
  ChevronLeft,
  ChevronRight,
  X,
  Radio,
} from "lucide-react";
import { PAGES } from "../../lib/constants";
import type { City } from "../../types";

export interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  city: City | string;
  className?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({
  currentPage,
  onNavigate,
  city,
  className = "",
  isCollapsed = false,
  onToggleCollapse,
  isMobileOpen = false,
  onCloseMobile,
}: SidebarProps) {
  const currentSlug = currentPage.toLowerCase();

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`sidebar ${isCollapsed ? "collapsed" : "expanded"} ${
          isMobileOpen ? "mobile-open" : ""
        } ${className}`.trim()}
        aria-label="Primary Navigation"
      >
        {/* Brand Header */}
        <div className="brand">
          <div className="brand-mark" title="Heatwise Climate Intelligence Platform">
            <Sparkles size={16} />
          </div>

          {!isCollapsed && (
            <div className="brand-text">
              <h1>Heatwise</h1>
              <p>Climate Intelligence</p>
            </div>
          )}

          {/* Desktop collapse toggle */}
          {onToggleCollapse && (
            <button
              type="button"
              className="sidebar-toggle-btn"
              onClick={onToggleCollapse}
              title={isCollapsed ? "Expand sidebar (240px)" : "Collapse sidebar to rail (64px)"}
              aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
          )}

          {/* Mobile close button */}
          {onCloseMobile && (
            <button
              type="button"
              className="sidebar-mobile-close"
              onClick={onCloseMobile}
              title="Close menu"
              aria-label="Close navigation"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Navigation Item List */}
        <nav className="nav" role="navigation">
          {!isCollapsed && <div className="nav-group-header">CANONICAL VIEWS</div>}

          {PAGES.map(({ slug, title, icon: Icon }) => {
            const isActive =
              currentPage === title ||
              currentPage === slug ||
              currentSlug === slug ||
              (slug === "prediction" && (currentSlug === "heat" || currentSlug === "predictions")) ||
              (slug === "simulator" && (currentSlug === "simulations" || currentSlug === "simulation"));

            return (
              <button
                key={slug}
                type="button"
                className={`nav-item ${isActive ? "active" : ""}`}
                onClick={() => {
                  onNavigate(title);
                  onCloseMobile?.();
                }}
                title={isCollapsed ? title : undefined}
                aria-current={isActive ? "page" : undefined}
              >
                <div className="nav-item-icon">
                  <Icon size={16} />
                </div>
                {!isCollapsed && (
                  <>
                    <span className="nav-item-title">{title}</span>
                    {isActive && <div className="nav-active-pill" />}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer / City Telemetry Card */}
        <div className="sidebar-foot">
          {!isCollapsed ? (
            <div className="city-telemetry-card">
              <div className="city-telemetry-header">
                <Radio size={12} className="pulse-dot-icon text-emerald-400" />
                <span className="city-telemetry-label">Active City Region</span>
              </div>
              <strong className="city-telemetry-name">{city}</strong>
              <div className="city-telemetry-provenance">
                <span>Analytical Grid</span>
                <span className="font-mono text-cyan-400">AMC Wards</span>
              </div>
            </div>
          ) : (
            <div
              className="city-telemetry-mini"
              title={`Active City: ${city} (AMC Municipal Analysis)`}
            >
              <Radio size={14} className="text-emerald-400" />
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
