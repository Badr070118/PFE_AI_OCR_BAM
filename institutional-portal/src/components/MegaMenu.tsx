import { Link } from "react-router-dom";
import type { NavItem } from "../data/navigation";

type MegaMenuProps = {
  item: NavItem;
  onClose?: () => void;
};

export default function MegaMenu({ item, onClose }: MegaMenuProps) {
  if (!item.columns?.length) {
    return null;
  }

  return (
    <div
      className="nav-shadow absolute left-0 right-0 top-full z-50 mt-2 hidden rounded-2xl border border-border bg-surface p-5 lg:block"
      role="menu"
      aria-label={`Sous-navigation ${item.label}`}
    >
      <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr] xl:grid-cols-2">
        {item.columns.map((column) => (
          <div key={column.title} className="rounded-xl border border-border/70 bg-white p-4">
            <div className="mb-3 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
              <h3 className="text-sm font-semibold uppercase tracking-[0.08em] text-primary">{column.title}</h3>
            </div>
            <ul className="space-y-2">
              {column.links.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.href}
                    onClick={onClose}
                    className="group block rounded-lg border border-transparent p-2 transition hover:border-border hover:bg-surfaceSoft"
                    role="menuitem"
                  >
                    <div className="text-sm font-medium text-ink group-hover:text-primary">{link.label}</div>
                    {link.description ? (
                      <div className="mt-1 text-xs leading-5 text-muted">{link.description}</div>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
