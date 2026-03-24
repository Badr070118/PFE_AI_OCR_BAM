const ARABIC_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
const ARABIC_TOKEN_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+/;
const LRI = "\u2066";
const RLI = "\u2067";
const PDI = "\u2069";

const isolate = (text, dir) => {
  if (!text) return "";
  return `${dir === "rtl" ? RLI : LRI}${text}${PDI}`;
};

export function formatPlateDisplay(value) {
  if (!value) return value;
  const raw = String(value).trim();
  if (!raw) return raw;

  const tokens = raw
    .split(/[-|\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  const normalizedTokens = tokens.length > 0 ? tokens : [];

  let arabicToken = normalizedTokens.find((part) => ARABIC_REGEX.test(part));
  if (!arabicToken) {
    arabicToken = normalizedTokens.find((part) => !/^\d+$/.test(part));
  }
  if (!arabicToken) {
    arabicToken = raw.match(ARABIC_TOKEN_REGEX)?.[0] || raw.match(/[^\d\s\-|]+/)?.[0] || "";
  }
  if (!arabicToken) return raw;

  const remaining = [...normalizedTokens];
  const index = remaining.findIndex((part) => part === arabicToken);
  if (index >= 0) {
    remaining.splice(index, 1);
  }

  let numeric = remaining.filter((part) => /^\d+$/.test(part));
  if (numeric.length < 2) {
    const extracted = raw.match(/\d+/g) || [];
    if (extracted.length >= 1) numeric = extracted;
  }
  let left = "";
  let right = "";

  if (numeric.length >= 2) {
    left = numeric[0];
    right = numeric[numeric.length - 1] || "";
    if (right === left && numeric.length > 1) {
      right = numeric[1] || "";
    }
  } else if (numeric.length === 1) {
    left = numeric[0];
    right = remaining.find((part) => part !== left) || "";
  } else {
    left = remaining[0] || "";
    right = remaining.slice(1).join("");
  }

  if (left && right) return `${isolate(left, "ltr")} - ${isolate(arabicToken, "rtl")} - ${isolate(right, "ltr")}`;
  if (left) return `${isolate(left, "ltr")} - ${isolate(arabicToken, "rtl")}`;
  if (right) return `${isolate(arabicToken, "rtl")} - ${isolate(right, "ltr")}`;
  return raw;
}
