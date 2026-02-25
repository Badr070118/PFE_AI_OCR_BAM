import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
};

export default function Card({ children, className = "", interactive = false }: CardProps) {
  return (
    <div
      className={[
        "institution-card rounded-2xl border bg-surface p-5 sm:p-6",
        interactive ? "transition-transform duration-200 hover:-translate-y-0.5 hover:border-primary/25" : "",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}
