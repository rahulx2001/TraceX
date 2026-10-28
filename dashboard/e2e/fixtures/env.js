/**
 * Shared runtime for the Playwright suite.
 * The key comes from the environment only. There is no checked-in fallback.
 */
export const BASE = process.env.BASE_URL || "http://127.0.0.1:8000";

export function apiKey() {
  const key = (process.env.E2E_API_KEY || process.env.FRONTLINE_API_KEY || "").trim();
  if (!key) {
    throw new Error(
      "Set E2E_API_KEY or FRONTLINE_API_KEY before Playwright. The suite does not ship a fallback key.",
    );
  }
  return key;
}
