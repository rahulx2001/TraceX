import { useEffect, useRef, useState } from "react";
import { SEVERITIES, contactHeatmap, countScale, forecastValues, paretoData, rollingAverage } from "./analyticsData.js";

const number = (n) => Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 });
const pct = (n) => `${Math.round(n * 100)}%`;
const LEFT = 40;
const TOP = 20;
const BASE = 222;
const HEIGHT = 258;

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    if (!ref.current) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function Legend({ items }) {
  return <div className="analysis-legend">{items.map((item) => (
    <span key={item.label}><i style={{ background: item.color }} className={item.line ? "is-line" : ""} />{item.label}</span>
  ))}</div>;
}

function DataTable({ headers, rows }) {
  return (
    <details className="analysis-data">
      <summary>View chart data</summary>
      <div className="analysis-table-scroll">
        <table><thead><tr>{headers.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </details>
  );
}

function Axes({ width, scale, right = 16, yLabel = "Cases" }) {
  return <g className="analysis-axes">
    <text x={LEFT} y={10}>{yLabel}</text>
    {scale.ticks.map((tick) => {
      const y = BASE - tick / scale.max * (BASE - TOP);
      return <g key={tick}><line x1={LEFT} x2={width - right} y1={y} y2={y} /><text x={LEFT - 9} y={y + 4} textAnchor="end">{number(tick)}</text></g>;
    })}
  </g>;
}

function chartKeys(event, current, count, set) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key) || !count) return;
  event.preventDefault();
  const next = event.key === "Home" ? 0 : event.key === "End" ? count - 1 : current + (event.key === "ArrowRight" ? 1 : -1);
  set(Math.max(0, Math.min(count - 1, next)));
}

export function CaseTimeline({ data, unavailable = false }) {
  const [ref, width] = useWidth();
  const [mode, setMode] = useState("daily");
  const [selected, setSelected] = useState(null);
  const [showAverage, setShowAverage] = useState(true);
  const period = data.length >= 14 ? 7 : 3;
  const averages = rollingAverage(data.map((d) => d.total), period);
  let running = 0;
  const totals = data.map((d) => (running += d.total));
  const cumulative = mode === "cumulative";
  const scale = countScale(Math.max(0, ...(cumulative ? totals : data.map((d) => d.total))));
  const plotWidth = width - LEFT - 16;
  const step = plotWidth / Math.max(1, data.length);
  const x = (i) => LEFT + (i + 0.5) * step;
  const y = (v) => BASE - v / scale.max * (BASE - TOP);
  const index = Math.min(selected ?? data.length - 1, data.length - 1);
  const active = data[index];
  const labelEvery = Math.max(1, Math.ceil(data.length / Math.max(2, Math.floor(plotWidth / 70))));
  const line = (values) => values.map((v, i) => v === null ? null : `${i === 0 || values[i - 1] === null ? "M" : "L"}${x(i)},${y(v)}`).filter(Boolean).join(" ");
  return (
    <div ref={ref}>
      <div className="analysis-chart-toolbar">
        <div className="analysis-segmented" aria-label="Case trend display">
          {["daily", "cumulative"].map((value) => <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)}>{value === "daily" ? "Daily" : "Cumulative"}</button>)}
        </div>
        {!cumulative && data.length >= period && <label className="analysis-check"><input type="checkbox" checked={showAverage} onChange={(e) => setShowAverage(e.target.checked)} />{period}-day average</label>}
      </div>
      {unavailable ? <div className="analysis-empty">Case data unavailable. Refresh to try again.</div> : <>
        <svg className="analysis-plot" viewBox={`0 0 ${width} ${HEIGHT}`} role="img" tabIndex={0}
          aria-label={`${cumulative ? "Cumulative cases" : "Daily cases by severity"}. ${running} cases. Use left and right arrow keys to inspect dates.`}
          onKeyDown={(e) => chartKeys(e, index, data.length, setSelected)}
          onPointerMove={(e) => setSelected(Math.max(0, Math.min(data.length - 1, Math.floor((e.clientX - e.currentTarget.getBoundingClientRect().left - LEFT) / step))))}>
          <Axes width={width} scale={scale} />
          {active && <rect className="analysis-highlight" x={x(index) - step / 2} y={TOP} width={step} height={BASE - TOP} rx="4" />}
          {cumulative ? <>
            <path d={`${line(totals)} L${x(data.length - 1)},${BASE} L${x(0)},${BASE} Z`} fill="var(--analysis-volume)" opacity=".09" />
            <path d={line(totals)} className="analysis-line" stroke="var(--analysis-volume)" />
            {totals.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={i === index ? 4 : 2} fill="var(--analysis-volume)" />)}
          </> : data.map((d, i) => {
            let stacked = 0;
            return <g key={d.key}>{SEVERITIES.map((s) => {
              const value = d[s.key];
              stacked += value;
              return value > 0 && <rect key={s.key} x={x(i) - Math.min(30, step * .55) / 2} y={y(stacked)} width={Math.min(30, step * .55)} height={BASE - y(value)} fill={s.color} rx="2"><title>{`${d.key}: ${value} ${s.key.toLowerCase()} cases`}</title></rect>;
            })}</g>;
          })}
          {!cumulative && showAverage && <>
            <path d={line(averages)} className="analysis-line" stroke="var(--analysis-volume)" strokeDasharray="5 4" />
            {averages.map((v, i) => v !== null && <circle key={i} cx={x(i)} cy={y(v)} r="2.5" fill="var(--analysis-volume)" />)}
          </>}
          {data.map((d, i) => (i % labelEvery === 0 || i === data.length - 1) && <text key={d.key} x={x(i)} y={BASE + 24} className="analysis-axis-label" textAnchor="middle">{d.key.slice(5)}</text>)}
        </svg>
        <div className="analysis-readout" aria-live="polite">
          <span>{active?.key} <span className="muted">UTC</span></span>
          <strong>{number(cumulative ? totals[index] || 0 : active?.total || 0)} {cumulative ? "cumulative cases" : "cases"}</strong>
          {!cumulative && showAverage && averages[index] != null && <span className="muted">{period}-day avg {number(averages[index])}</span>}
        </div>
        <Legend items={cumulative ? [{ label: "Cumulative cases", color: "var(--analysis-volume)", line: true }] : [
          ...SEVERITIES.filter((s) => data.some((d) => d[s.key] > 0)).map((s) => ({ label: s.key, color: s.color })),
          ...(showAverage && data.length >= period ? [{ label: `${period}-day average`, color: "var(--analysis-volume)", line: true }] : []),
        ]} />
        {running === 0 && <p className="analysis-note">No cases created in this window in the loaded sample.</p>}
        <DataTable headers={["Date (UTC)", "Total", ...SEVERITIES.map((s) => s.key), `${period}-day average`]} rows={data.map((d, i) => [d.key, d.total, ...SEVERITIES.map((s) => d[s.key]), averages[i] == null ? "—" : number(averages[i])])} />
      </>}
    </div>
  );
}

export function SeverityRing({ data }) {
  const items = data.filter((d) => d.value > 0);
  const total = items.reduce((sum, d) => sum + d.value, 0);
  let offset = 0;
  return <div className="analysis-distribution">
    <svg viewBox="0 0 180 180" role="img" aria-label={`Severity distribution: ${items.map((d) => `${d.label} ${d.value}`).join(", ") || "no cases"}`}>
      <circle cx="90" cy="90" r="69" fill="none" stroke="var(--edge)" strokeWidth="13" />
      {items.map((item) => {
        const share = item.value / total * 100;
        const start = offset; offset += share;
        return <circle key={item.label} cx="90" cy="90" r="69" fill="none" stroke={SEVERITIES.find((s) => s.key === item.label)?.color || "var(--ink-soft)"} strokeWidth="13" pathLength="100" strokeDasharray={`${Math.max(0, share - (items.length > 1 ? 1.2 : 0))} ${100 - Math.max(0, share - (items.length > 1 ? 1.2 : 0))}`} strokeDashoffset={-start} transform="rotate(-90 90 90)"><title>{`${item.label}: ${item.value} (${pct(item.value / total)})`}</title></circle>;
      })}
      <text x="90" y="88" textAnchor="middle" className="analysis-ring-total">{number(total)}</text>
      <text x="90" y="110" textAnchor="middle" className="analysis-axis-label">sampled cases</text>
    </svg>
    <ul>{(items.length ? items : [{ label: "No cases in window", value: 0 }]).map((item) => <li key={item.label}>
      <span><i style={{ background: SEVERITIES.find((s) => s.key === item.label)?.color || "var(--ink-soft)" }} />{item.label}</span>
      <strong>{item.value}</strong><span className="muted">{total ? pct(item.value / total) : "—"}</span>
    </li>)}</ul>
  </div>;
}

export function ParetoChart({ rows }) {
  const [ref, width] = useWidth();
  const [selected, setSelected] = useState(0);
  const data = paretoData(rows);
  const scale = countScale(Math.max(0, ...data.map((d) => d.value)));
  const right = 40;
  const step = (width - LEFT - right) / Math.max(1, data.length);
  const x = (i) => LEFT + step * (i + .5);
  const y = (v) => BASE - v * (BASE - TOP);
  const index = Math.min(selected, data.length - 1);
  const active = data[index];
  return <div ref={ref}>
    {!data.length ? <div className="analysis-empty">No case categories in this window.</div> : <>
      <Legend items={[{ label: "Case volume", color: "var(--analysis-volume)" }, { label: "Cumulative share", color: "var(--warn)", line: true }]} />
      <svg className="analysis-plot" viewBox={`0 0 ${width} ${HEIGHT}`} role="img" tabIndex={0} aria-label="Category Pareto chart. Bars show case counts; line shows cumulative share. Use arrow keys to inspect categories."
        onKeyDown={(e) => chartKeys(e, index, data.length, setSelected)}
        onPointerMove={(e) => setSelected(Math.max(0, Math.min(data.length - 1, Math.floor((e.clientX - e.currentTarget.getBoundingClientRect().left - LEFT) / step))))}>
        <Axes width={width} scale={scale} right={right} />
        {[0, .5, 1].map((v) => <text key={v} x={width - right + 9} y={y(v) + 4} className="analysis-axis-label">{pct(v)}</text>)}
        <line x1={LEFT} x2={width - right} y1={y(.8)} y2={y(.8)} stroke="var(--warn)" strokeDasharray="3 5" opacity=".5" />
        <text x={width - right - 4} y={y(.8) - 7} textAnchor="end" className="analysis-axis-label">80% reference</text>
        {data.map((d, i) => <g key={d.label}>
          <rect x={x(i) - Math.min(40, step * .55) / 2} y={y(d.value / scale.max)} width={Math.min(40, step * .55)} height={BASE - y(d.value / scale.max)} rx="4" fill="var(--analysis-volume)" opacity={i === index ? 1 : .55}><title>{`${d.label}: ${d.value} cases; cumulative ${pct(d.cumulative)}`}</title></rect>
          <text x={x(i)} y={BASE + 24} textAnchor="middle" className="analysis-axis-label">{i + 1}</text>
        </g>)}
        <path className="analysis-line" stroke="var(--warn)" d={data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(d.cumulative)}`).join(" ")} />
        {data.map((d, i) => <circle key={i} cx={x(i)} cy={y(d.cumulative)} r={i === index ? 5 : 3} fill="var(--warn)" stroke="var(--bg-panel)" strokeWidth="2" />)}
      </svg>
      <div className="analysis-readout" aria-live="polite"><strong>{index + 1}. {active.label}</strong><span>{active.value} cases · {pct(active.cumulative)} cumulative</span></div>
      <ol className="analysis-category-key">{data.map((d, i) => <li key={d.label}><button type="button" aria-pressed={i === index} onClick={() => setSelected(i)}><span>{i + 1}</span>{d.label}</button></li>)}</ol>
      <DataTable headers={["Category", "Cases", "Share", "Cumulative share"]} rows={data.map((d) => [d.label, d.value, pct(d.share), pct(d.cumulative)])} />
    </>}
  </div>;
}

export function ForecastChart({ forecasts }) {
  const [ref, width] = useWidth();
  const [cluster, setCluster] = useState("");
  const f = forecasts.find((item) => String(item.cluster_id) === cluster) || forecasts[0];
  const { history, projected, interval } = forecastValues(f);
  const threshold = f?.threshold != null && Number.isFinite(Number(f.threshold)) ? Number(f.threshold) : null;
  const scale = countScale(Math.max(0, ...history, projected || 0, interval?.[1] || 0, threshold || 0));
  const slots = Math.max(4, history.length + 1);
  const x = (i) => LEFT + (width - LEFT - 30) * i / (slots - 1);
  const y = (v) => BASE - v / scale.max * (BASE - TOP);
  const nextX = x(history.length);
  const lastX = x(history.length - 1);
  const predictionLabel = projected === null ? "Insufficient history for a projection." : `Next week ${number(projected)}. ${interval ? `95% prediction interval ${number(interval[0])} to ${number(interval[1])}.` : ""}`;
  return <div ref={ref}>
    {f && <div className="analysis-chart-toolbar"><select aria-label="Forecast cluster" value={String(f.cluster_id)} onChange={(e) => setCluster(e.target.value)}>{forecasts.map((row) => <option key={row.cluster_id} value={row.cluster_id}>Cluster {row.cluster_id}</option>)}</select><span className="analysis-note">{history.length} observed weeks</span></div>}
    {!history.length ? <div className="analysis-empty">No weekly history available for a forecast.</div> : <>
      <svg className="analysis-plot" viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label={`Cluster ${f.cluster_id}. Weekly observations ${history.join(", ")}. ${predictionLabel}`}>
        <Axes width={width} scale={scale} yLabel="Weekly cases" right={30} />
        <rect x={Math.max(LEFT, lastX + 4)} y={TOP} width={Math.max(0, nextX - lastX - 4)} height={BASE - TOP} fill="var(--analysis-volume)" opacity=".05" />
        {threshold !== null && <><line x1={LEFT} x2={width - 30} y1={y(threshold)} y2={y(threshold)} stroke="var(--danger)" strokeDasharray="4 5" opacity=".7" /><text x={width - 32} y={y(threshold) - 6} textAnchor="end" className="analysis-axis-label">Threshold {number(threshold)}</text></>}
        {interval && <><path d={`M${lastX},${y(history.at(-1))} L${nextX},${y(interval[1])} L${nextX},${y(interval[0])} Z`} fill="var(--analysis-volume)" opacity=".15" /><line x1={nextX} x2={nextX} y1={y(interval[0])} y2={y(interval[1])} stroke="var(--analysis-volume)" strokeWidth="2" /></>}
        <path d={history.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ")} className="analysis-line" stroke="var(--ink-soft)" />
        {history.map((v, i) => <g key={i}><circle cx={x(i)} cy={y(v)} r="4" fill="var(--ink-soft)"><title>{`Observation ${i + 1}: ${v} cases`}</title></circle><text x={x(i)} y={BASE + 24} textAnchor="middle" className="analysis-axis-label">W{i + 1}</text></g>)}
        {projected !== null && <><line x1={lastX} x2={nextX} y1={y(history.at(-1))} y2={y(projected)} className="analysis-line" stroke="var(--analysis-volume)" strokeDasharray="5 4" /><circle cx={nextX} cy={y(projected)} r="5" fill="var(--analysis-volume)" /><text x={nextX} y={BASE + 24} textAnchor="middle" className="analysis-axis-label">Next</text></>}
      </svg>
      <Legend items={[{ label: "Observed", color: "var(--ink-soft)", line: true }, ...(projected !== null ? [{ label: "Projection", color: "var(--analysis-volume)", line: true }] : []), ...(interval ? [{ label: "95% prediction interval", color: "var(--analysis-volume)" }] : [])]} />
      <div className="analysis-readout"><strong>{projected === null ? "More history needed" : `${number(projected)} projected cases`}</strong><span>{projected === null ? "At least 4 weekly observations required" : interval ? `95% range ${number(interval[0])}–${number(interval[1])}` : "Prediction interval unavailable"}</span></div>
      <p className="analysis-note">W1–W{history.length} label recorded observations, not calendar weeks. Empty weeks may be absent.</p>
    </>}
  </div>;
}

export function SeverityDriftChart({ rows }) {
  const [ref, width] = useWidth();
  const data = [...rows].sort((a, b) => b.severity_drift - a.severity_drift).slice(0, 8);
  const x = (v) => 92 + (v - 1) / 2 * Math.max(40, width - 180);
  const height = Math.max(130, data.length * 40 + 50);
  return <div ref={ref}>
    {!data.length ? <div className="analysis-empty">No severity history to compare.</div> : <>
      <Legend items={[{ label: "Earlier half", color: "var(--ink-soft)" }, { label: "Later half", color: "var(--warn)" }]} />
      <svg className="analysis-drift-plot" style={{ height }} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Severity shift by cluster, from earlier to later half. Scale: low 1, medium 2, critical 3. Values are available in the table below.">
        {[1, 2, 3].map((v) => <g key={v}><line x1={x(v)} x2={x(v)} y1="12" y2={height - 30} className="analysis-grid-line" /><text x={x(v)} y={height - 8} textAnchor="middle" className="analysis-axis-label">{["Low", "Medium", "Critical"][v - 1]} · {v}</text></g>)}
        {data.map((d, i) => {
          const y = 26 + i * 40;
          const early = Number(d.early_avg_severity), late = Number(d.late_avg_severity);
          const paired = early >= 1 && late >= 1;
          const color = late > early && paired ? "var(--danger)" : late < early && paired ? "var(--ok)" : "var(--warn)";
          return <g key={d.cluster_id}><text x="0" y={y + 4} className="analysis-axis-label">#{d.cluster_id}</text>
            {paired && <line x1={x(early)} x2={x(late)} y1={y} y2={y} stroke={color} strokeWidth="4" opacity=".6" />}
            {early >= 1 && <circle cx={x(early)} cy={y} r="5" fill="var(--bg-panel)" stroke="var(--ink-soft)" strokeWidth="2"><title>{`Earlier: ${early}`}</title></circle>}
            {late >= 1 && <circle cx={x(late)} cy={y} r="5" fill={color}><title>{`Later: ${late}`}</title></circle>}
            <text x={width - 4} y={y + 4} textAnchor="end" className="analysis-axis-label">{paired ? `${late - early > 0 ? "+" : ""}${number(late - early)}` : "No pair"}</text>
          </g>;
        })}
      </svg>
      <p className="analysis-note">Connected dots show a change. “No pair” means one period has no scored data.</p>
    </>}
  </div>;
}

export function ActivityHeatmap({ rows, days }) {
  const data = contactHeatmap(rows, days);
  const max = Math.max(1, ...data.flatMap((d) => d.hours));
  return <div>
    <div className="analysis-table-scroll">
      <table className="analysis-heatmap"><caption className="sr-only">Sampled contacts by UTC date and hour</caption>
        <thead><tr><th scope="col">UTC</th>{Array.from({ length: 24 }, (_, h) => <th key={h} scope="col">{String(h).padStart(2, "0")}</th>)}</tr></thead>
        <tbody>{data.map((d) => <tr key={d.key}><th scope="row">{d.key.slice(5)}</th>{d.hours.map((v, h) => <td key={h} title={`${d.key}, ${h}:00 UTC: ${v} sampled contacts`} aria-label={`${d.key}, ${h}:00 UTC: ${v} sampled contacts`} style={v ? { background: `color-mix(in srgb, var(--analysis-volume) ${20 + v / max * 60}%, var(--bg-panel))`, color: "var(--ink)" } : undefined}>{v || <span aria-hidden="true">·</span>}</td>)}</tr>)}</tbody>
      </table>
    </div>
    <div className="analysis-heatmap-legend" aria-label={`Color scale: 0 to ${max} sampled contacts per hour`}>
      <span>0</span>{[0, 20, 40, 60, 80].map((strength) => <i key={strength} aria-hidden="true" style={{ background: strength ? `color-mix(in srgb, var(--analysis-volume) ${strength}%, var(--bg-panel))` : "var(--bg-hover)" }} />)}<span>{max} contacts / hour</span>
    </div>
    <p className="analysis-note">Sampled audit contacts only. Hover a cell for its date, hour and count.</p>
  </div>;
}
