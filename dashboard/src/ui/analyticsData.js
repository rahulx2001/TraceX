export const SEVERITIES = [
  { key: "Low", color: "var(--ok)" },
  { key: "Medium", color: "var(--warn)" },
  { key: "Critical", color: "var(--danger)" },
  { key: "Unknown", color: "var(--ink-soft)" },
];

// Warehouse timestamps without an offset are UTC, not browser-local time.
export function utcDate(value) {
  if (!value) return null;
  const s = String(value).trim().replace(" ", "T");
  const d = new Date(s.length > 10 && !/(Z|[+-]\d{2}:?\d{2})$/i.test(s) ? `${s}Z` : s);
  return Number.isFinite(d.getTime()) ? d : null;
}

export function utcDays(days, now = new Date()) {
  const end = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Array.from({ length: days }, (_, i) => new Date(end - (days - 1 - i) * 86400000).toISOString().slice(0, 10));
}

export function casesInWindow(rows, days, now = new Date()) {
  const keys = new Set(utcDays(days, now));
  return (rows || []).filter((row) => {
    const date = utcDate(row.created_at);
    return date && keys.has(date.toISOString().slice(0, 10));
  });
}

export function dailySeverity(rows, days, now = new Date()) {
  const buckets = utcDays(days, now).map((key) => ({ key, total: 0, Low: 0, Medium: 0, Critical: 0, Unknown: 0 }));
  const byDay = new Map(buckets.map((b) => [b.key, b]));
  for (const row of rows || []) {
    const date = utcDate(row.created_at);
    const b = date && byDay.get(date.toISOString().slice(0, 10));
    if (!b) continue;
    const severity = SEVERITIES.find((s) => s.key.toLowerCase() === String(row.severity).toLowerCase())?.key || "Unknown";
    b[severity] += 1;
    b.total += 1;
  }
  return buckets;
}

export function rollingAverage(values, period) {
  return values.map((_, i) => i + 1 < period ? null : values.slice(i + 1 - period, i + 1).reduce((a, b) => a + b, 0) / period);
}

export function paretoData(rows, limit = 7) {
  const counts = new Map();
  for (const row of rows || []) {
    const label = row.category || "Uncategorized";
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  const ranked = [...counts].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value || a.label.localeCompare(b.label));
  const total = ranked.reduce((sum, row) => sum + row.value, 0);
  const visible = ranked.slice(0, limit);
  if (ranked.length > limit) visible.push({ label: `Other (${ranked.length - limit} categories)`, value: ranked.slice(limit).reduce((sum, row) => sum + row.value, 0) });
  let cumulative = 0;
  return visible.map((row) => {
    cumulative += row.value;
    return { ...row, share: row.value / total, cumulative: cumulative / total };
  });
}

export function countScale(max) {
  if (!(max > 1)) return { max: 1, ticks: [0, 1] };
  const raw = max / 4;
  const unit = 10 ** Math.floor(Math.log10(raw));
  const step = Math.max(1, [1, 2, 5, 10].find((n) => n * unit >= raw) * unit);
  const top = Math.ceil(max / step) * step;
  return { max: top, ticks: Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step) };
}

export function forecastValues(forecast) {
  const finite = (v) => v != null && v !== "" && Number.isFinite(Number(v));
  const history = (forecast?.weekly_counts || []).filter(finite).map(Number);
  const eligible = forecast?.status !== "insufficient_history" && forecast?.forecast_method !== "insufficient_history";
  const projected = eligible && finite(forecast?.projected_next_week) ? Number(forecast.projected_next_week) : null;
  const interval = projected !== null && finite(forecast?.ci_low) && finite(forecast?.ci_high) && Number(forecast.ci_low) <= Number(forecast.ci_high)
    ? [Number(forecast.ci_low), Number(forecast.ci_high)] : null;
  return { history, projected, interval };
}

export function contactHeatmap(rows, days, now = new Date()) {
  const buckets = utcDays(days, now).map((key) => ({ key, hours: Array(24).fill(0) }));
  const map = new Map(buckets.map((b) => [b.key, b]));
  for (const row of rows || []) {
    const date = utcDate(row.started_at);
    const bucket = date && map.get(date.toISOString().slice(0, 10));
    if (bucket) bucket.hours[date.getUTCHours()] += 1;
  }
  return buckets;
}
