import React from "react";
import { Info } from "lucide-react";

export interface NoticeProps {
  tone?: "info" | "neutral" | "warn";
  children: React.ReactNode;
  className?: string;
}

export function Notice({ tone = "neutral", children, className = "" }: NoticeProps) {
  return (
    <div className={`notice ${tone}${className ? ` ${className}` : ""}`}>
      <Info size={14} className="shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  );
}
