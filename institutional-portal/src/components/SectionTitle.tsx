import type { ReactNode } from "react";
import Badge from "./Badge";

type SectionTitleProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

export default function SectionTitle({ eyebrow, title, subtitle, actions }: SectionTitleProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl space-y-2">
        {eyebrow ? <Badge tone="accent">{eyebrow}</Badge> : null}
        <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h2>
        {subtitle ? <p className="text-sm leading-6 text-muted sm:text-base">{subtitle}</p> : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  );
}
