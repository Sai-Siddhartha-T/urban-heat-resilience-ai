import React from "react";
import { AlertTriangle } from "lucide-react";
import type { DatasetMetadata } from "../../types/geojson";

export type SyntheticMetadataInput =
  | Partial<DatasetMetadata>
  | {
      isSynthetic?: boolean;
      synthetic?: boolean;
      source?: string;
    }
  | null;

export interface SyntheticWarningBadgeProps {
  metadata?: SyntheticMetadataInput;
  isSynthetic?: boolean;
  className?: string;
  showIcon?: boolean;
  children?: React.ReactNode;
}

export function SyntheticWarningBadge({
  metadata,
  isSynthetic,
  className = "",
  showIcon = true,
  children,
}: SyntheticWarningBadgeProps) {
  const isFallback = Boolean(
    isSynthetic ??
      metadata?.isSynthetic ??
      metadata?.synthetic ??
      (typeof metadata?.source === "string" && metadata.source.toLowerCase().includes("synthetic"))
  );

  if (!isFallback) {
    return null;
  }

  return (
    <div
      className={`synthetic-warning-badge ${className}`.trim()}
      role="status"
      aria-label="Synthetic Data Warning"
      data-testid="synthetic-warning-badge"
    >
      {showIcon && <AlertTriangle size={13} className="shrink-0 text-amber-700" />}
      <span>{children ?? "Synthetic Fallback Data"}</span>
    </div>
  );
}

export default SyntheticWarningBadge;
