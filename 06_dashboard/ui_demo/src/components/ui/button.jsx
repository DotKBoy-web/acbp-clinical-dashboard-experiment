import React from "react";

export default function Button({
  children,
  onClick,
  disabled = false,
  active = false,
  variant = "default",
  size = "default",
  className = "",
}) {
  const baseClasses =
    "inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-400";

  const sizeClasses = {
    sm: "h-7 rounded-lg px-2.5 text-[11px] gap-1",
    default: "h-9 rounded-xl px-4 text-xs gap-1.5",
    lg: "h-11 rounded-2xl px-5 text-sm gap-2",
  };

  const variantClasses = {
    default: active
      ? "bg-slate-900 text-white shadow-lg shadow-slate-900/20 hover:bg-slate-800"
      : "border-2 border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 hover:shadow-md active:bg-slate-100",
    primary:
      "bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25 hover:from-emerald-600 hover:to-teal-700 hover:shadow-xl hover:shadow-emerald-500/30 active:scale-[0.98]",
    danger:
      "bg-gradient-to-r from-rose-500 to-red-600 text-white shadow-lg shadow-rose-500/25 hover:from-rose-600 hover:to-red-700 hover:shadow-xl hover:shadow-rose-500/30 active:scale-[0.98]",
    ghost:
      "text-slate-600 hover:bg-slate-100 hover:text-slate-900 active:bg-slate-200",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`
        ${baseClasses}
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${disabled ? "cursor-not-allowed opacity-50 grayscale" : "cursor-pointer"}
        ${className}
      `}
    >
      {children}
    </button>
  );
}