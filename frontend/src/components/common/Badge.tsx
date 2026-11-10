import React from "react";
import type { Tone } from "../../types/common";

export interface BadgeProps {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ tone = "neutral", children, className = "" }: BadgeProps) {
  return (
    <span className={`badge ${tone}${className ? ` ${className}` : ""}`}>
      {children}
    </span>
  );
}
