import test from "node:test";
import assert from "node:assert/strict";
import { casesInWindow, dailySeverity, rollingAverage, paretoData, forecastValues, countScale, contactHeatmap } from "../src/ui/analyticsData.js";

const now = new Date("2026-10-29T10:00:00Z");

test("UTC window boundaries, missing days, and unknown severity preserve true counts", () => {
  const rows = [
    { created_at: "2026-10-27 00:00:00", severity: "Critical" },
    { created_at: "2026-10-29T00:30:00+05:30", severity: "medium" },
    { created_at: "2026-10-29T09:00:00Z", severity: null },
    { created_at: "2026-10-26T23:59:59Z", severity: "Low" },
    { created_at: "2026-10-30T00:00:00Z", severity: "Low" },
    { created_at: "invalid", severity: "Low" },
  ];
  assert.equal(casesInWindow(rows, 3, now).length, 3);
  const days = dailySeverity(rows, 3, now);
  assert.deepEqual(days.map((d) => d.total), [1, 1, 1]);
  assert.equal(days[1].Medium, 1);
  assert.equal(days[2].Unknown, 1);
  assert.deepEqual(dailySeverity([], 3, now).map((d) => d.total), [0, 0, 0]);
  assert.equal(casesInWindow(rows, 1, now).length, 1);
});

test("rolling average includes zero-volume days and needs a complete window", () => {
  assert.deepEqual(rollingAverage([6, 0, 0, 3], 3), [null, null, 2, 1]);
});

test("Pareto retains the full denominator when grouping smaller categories", () => {
  const rows = ["A", "A", "A", "B", "B", "C", "D", null].map((category) => ({ category }));
  const data = paretoData(rows, 2);
  assert.deepEqual(data.map((d) => d.value), [3, 2, 3]);
  assert.equal(data[1].cumulative, 5 / 8);
  assert.equal(data.at(-1).cumulative, 1);
  assert.deepEqual(paretoData([]), []);
});

test("missing forecasts stay missing while a genuine zero projection is retained", () => {
  assert.equal(forecastValues({ weekly_counts: [2], projected_next_week: null }).projected, null);
  assert.equal(forecastValues({ forecast_method: "insufficient_history", projected_next_week: 3 }).projected, null);
  assert.deepEqual(forecastValues({ weekly_counts: [4, 3, 2, 1], projected_next_week: 0, ci_low: 0, ci_high: 2 }), { history: [4, 3, 2, 1], projected: 0, interval: [0, 2] });
  assert.equal(forecastValues({ projected_next_week: 5, ci_low: null, ci_high: null }).interval, null);
  assert.equal(forecastValues({ projected_next_week: 5, ci_low: 9, ci_high: 2 }).interval, null);
});

test("count axes keep integer ticks for sparse counts and cover large values", () => {
  for (const max of [0, 1, 2, 5, 17, 1200]) {
    const scale = countScale(max);
    assert.ok(scale.max >= max);
    assert.ok(scale.ticks.every(Number.isInteger));
    assert.equal(scale.ticks[0], 0);
  }
});

test("activity heatmap uses UTC hours and excludes out-of-window contacts", () => {
  const days = contactHeatmap([{ started_at: "2026-10-29T01:30:00+05:30" }, { started_at: "2026-10-29 05:00:00" }, { started_at: "2026-10-26T05:00:00Z" }], 2, now);
  assert.equal(days[0].hours[20], 1);
  assert.equal(days[1].hours[5], 1);
  assert.equal(days.flatMap((d) => d.hours).reduce((a, b) => a + b, 0), 2);
});
