import React from "react";
import { RefreshCw } from "lucide-react";

export interface PendingProps {
  message?: string;
  className?: string;
}

export function Pending({ message = "Loading…", className = "" }: PendingProps) {
  return (
    <div className={`pending${className ? ` ${className}` : ""}`}>
      <RefreshCw size={15} className="spin shrink-0" />
      <span>{message}</span>
    </div>
  );
}
