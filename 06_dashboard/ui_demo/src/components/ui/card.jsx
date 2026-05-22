import React from "react";

export default function Card({
  children,
  className = "",
  hover = false,
}) {
  return (
    <div
      className={`
        flex flex-col overflow-hidden rounded-3xl border border-slate-200/60 bg-white/90
        shadow-sm
        ${hover ? "hover-lift cursor-pointer" : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = "" }) {
  return (
    <div className={`shrink-0 flex items-start justify-between gap-3 p-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, icon: Icon, className = "" }) {
  return (
    <div className={className}>
      <h2 className="flex items-center gap-2 text-base font-bold text-slate-900 lg:text-lg">
        {Icon && <Icon className="h-5 w-5 text-slate-600 shrink-0" />}
        {children}
      </h2>
    </div>
  );
}

export function CardDescription({ children }) {
  return <p className="mt-0.5 text-xs text-slate-500">{children}</p>;
}

export function CardContent({ children, className = "" }) {
  return (
    <div className={`min-h-0 flex-1 overflow-auto p-4 pt-0 ${className}`}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = "" }) {
  return (
    <div className={`shrink-0 rounded-b-3xl bg-slate-50 p-3 text-[11px] text-slate-600 ${className}`}>
      {children}
    </div>
  );
}