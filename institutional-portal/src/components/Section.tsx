import type { ComponentPropsWithoutRef, ReactNode } from "react";
import Container from "./Container";

type SectionProps = {
  children: ReactNode;
  className?: string;
  tone?: "default" | "soft";
} & Omit<ComponentPropsWithoutRef<"section">, "className" | "children">;

export default function Section({ children, className = "", tone = "default", ...rest }: SectionProps) {
  return (
    <section className={`py-12 sm:py-16 ${tone === "soft" ? "bg-surface/60" : ""} ${className}`} {...rest}>
      <Container>{children}</Container>
    </section>
  );
}
