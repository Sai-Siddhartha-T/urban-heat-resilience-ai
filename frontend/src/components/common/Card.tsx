import React from "react";

export interface CardProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Card({
  title,
  subtitle,
  actions,
  action,
  children,
  className = "",
}: CardProps) {
  const headerActions = actions ?? action;
  return (
    <section className={`card ${className}`.trim()}>
      {(title || subtitle || headerActions) && (
        <header className="card-head">
          <div>
            {title && <h3>{title}</h3>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {headerActions}
        </header>
      )}
      {children}
    </section>
  );
}
