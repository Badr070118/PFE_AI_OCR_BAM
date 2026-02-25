import type { ReactNode } from "react";

type BadgeProps = {
  children: ReactNode;
  tone?: "accent" | "muted" | "primary";
  className?: string;
};

const toneMap = {
  accent: "bg-accent/10 text-accent border-accent/25",
  muted: "bg-surfaceSoft text-muted border-border",
  primary: "bg-primary/10 text-primary border-primary/20",
};

export default function Badge({ children, tone = "muted", className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${toneMap[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
