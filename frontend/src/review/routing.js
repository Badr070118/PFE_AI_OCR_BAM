import { useEffect, useMemo, useState } from "react";

const OCR_BASE = "/ocr";
const REVIEW_ROUTE_RE = /^\/ocr\/documents\/(\d+)\/review\/?$/i;

export function parseAppRoute(pathname) {
  const currentPath = pathname || "/";
  const match = REVIEW_ROUTE_RE.exec(pathname || "/");
  if (!match) {
    if (currentPath === OCR_BASE || currentPath === `${OCR_BASE}/`) {
      return { type: "home" };
    }
    return { type: "home" };
  }

  return {
    type: "review",
    documentId: Number(match[1]),
  };
}

export function navigateTo(pathname) {
  const nextPath = pathname.startsWith(OCR_BASE)
    ? pathname
    : `${OCR_BASE}${pathname === "/" ? "" : pathname}`;
  if (window.location.pathname === nextPath) {
    return;
  }
  window.history.pushState({}, "", nextPath);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function useAppRoute() {
  const [pathname, setPathname] = useState(window.location.pathname);

  useEffect(() => {
    const handlePathChange = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePathChange);
    return () => {
      window.removeEventListener("popstate", handlePathChange);
    };
  }, []);

  return useMemo(() => parseAppRoute(pathname), [pathname]);
}
