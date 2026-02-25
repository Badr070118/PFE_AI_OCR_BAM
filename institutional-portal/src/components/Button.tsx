import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

type CommonProps = {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  className?: string;
};

type LinkButtonProps = CommonProps & { to: string; href?: never } & Omit<LinkProps, "className" | "to">;
type AnchorButtonProps = CommonProps & { href: string; to?: never } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className">;
type NativeButtonProps = CommonProps & { to?: never; href?: never } & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

export type ButtonProps = LinkButtonProps | AnchorButtonProps | NativeButtonProps;

const variantMap = {
  primary:
    "bg-primary text-white hover:bg-primary-2 border border-transparent shadow-sm shadow-primary/20",
  secondary:
    "bg-white text-ink hover:bg-surfaceSoft border border-border shadow-sm",
  ghost:
    "bg-transparent text-primary hover:bg-primary/5 border border-transparent",
} as const;

const sizeMap = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm sm:text-[0.95rem]",
  lg: "px-5 py-2.5 text-sm sm:text-base",
} as const;

function classes(props: CommonProps) {
  return [
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors duration-150",
    variantMap[props.variant ?? "primary"],
    sizeMap[props.size ?? "md"],
    props.className ?? "",
  ].join(" ");
}

export default function Button(props: ButtonProps) {
  if ("to" in props && props.to) {
    const { children, to, variant, size, className, ...rest } = props;
    return (
      <Link to={to} className={classes({ children, variant, size, className })} {...rest}>
        {children}
      </Link>
    );
  }

  if ("href" in props && props.href) {
    const { children, href, variant, size, className, ...rest } = props;
    return (
      <a href={href} className={classes({ children, variant, size, className })} {...rest}>
        {children}
      </a>
    );
  }

  const { children, variant, size, className, ...rest } = props;
  const nativeProps = rest as ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button type={nativeProps.type ?? "button"} className={classes({ children, variant, size, className })} {...nativeProps}>
      {children}
    </button>
  );
}
