import { useEffect, useState } from "react";
import {
  apiHeaders,
  getStoredApiKey,
  notifyAuthChange,
  setApiKey as storeApiKey,
} from "../src/apiAuth.js";
import { hashQueryObject, patchHashQuery, simulateTraffic } from "../src/ui/opsActions.js";
import { Banner, bannerTone } from "../src/ui/Feedback.jsx";
import { aiStatus } from "../src/ai/aiApi.js";
import PackBuilder from "./PackBuilder.jsx";
import FeatureStudio from "./FeatureStudio.jsx";
import "./settings.css";

export default function Settings() {
  const panel = hashQueryObject().tab || "general";
  const [simBusy, setSimBusy] = useState(false);
  const [simMsg, setSimMsg] = useState(null);
  const [packs, setPacks] = useState([]);
  const [active, setActive] = useState(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState(null);
  const [alertWebhook, setAlertWebhook] = useState("");
  const [apiKey, setApiKey] = useState(() => getStoredApiKey());
  // Explicit opt-in persistence (item 20): memory-only by default, disk
  // only when the operator checks "Remember on this device".
  const [rememberKey, setRememberKey] = useState(false);
  const [authRequired, setAuthRequired] = useState(null);
  const [deadLetters, setDeadLetters] = useState([]);
  const [dlLoading, setDlLoading] = useState(false);
  const [dlMsg, setDlMsg] = useState(null);
  const [singleWorker, setSingleWorker] = useState(null);
  const [connEnabled, setConnEnabled] = useState(false);
  const [connUrl, setConnUrl] = useState("");
  const [connSecret, setConnSecret] = useState("");
  const [connStatus, setConnStatus] = useState(null);
  const [connDeliveries, setConnDeliveries] = useState([]);
  const [connMsg, setConnMsg] = useState(null);
  const [connLoading, setConnLoading] = useState(false);
  const [connSaving, setConnSaving] = useState(false);
  const [statusRefresh, setStatusRefresh] = useState(0);
  // [AI-LAYER] Server-side Meta key status — GET /api/ai/status only. The
  // dashboard never receives or sends the Meta key itself.
  const [metaStatus, setMetaStatus] = useState(null);

  useEffect(() => {
    let live = true;
    aiStatus({ refresh: true })
      .then((s) => { if (live) setMetaStatus(s || { unavailable: true }); })
      .catch(() => { if (live) setMetaStatus({ unavailable: true }); });
    return () => { live = false; };
  }, [panel, statusRefresh]);

  // All requests go through the centralized credential helper
  // (src/apiAuth.js) — no direct storage reads in components (item 46).

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/packs", { headers: apiHeaders() });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setPacks(d.packs || []);
      setActive(d.active || null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadDeadLetters({ preserveMessage = false } = {}) {
    setDlLoading(true);
    if (!preserveMessage) setDlMsg(null);
    try {
      const r = await fetch("/api/frontline/alerts/dead-letter?status=pending&limit=50", {
        headers: apiHeaders(),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      const d = await r.json();
      setDeadLetters(d.dead_letters || []);
    } catch (e) {
      setDlMsg(String(e));
      setDeadLetters([]);
    } finally {
      setDlLoading(false);
    }
  }

  async function replayDeadLetter(id) {
    setDlMsg(null);
    try {
      const r = await fetch(
        `/api/frontline/alerts/dead-letter/${encodeURIComponent(id)}/replay`,
        { method: "POST", headers: apiHeaders() }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      setDlMsg(`Replayed ${id}`);
      await loadDeadLetters({ preserveMessage: true });
    } catch (e) {
      setDlMsg(String(e));
    }
  }

  async function loadConnector({ preserveMessage = false } = {}) {
    setConnLoading(true);
    if (!preserveMessage) setConnMsg(null);
    try {
      const [st, dl] = await Promise.all([
        fetch("/api/frontline/connectors/status", { headers: apiHeaders() }),
        fetch("/api/frontline/connectors/deliveries?status=pending&limit=50", {
          headers: apiHeaders(),
        }),
      ]);
      if (!st.ok) throw new Error(`status HTTP ${st.status}`);
      if (!dl.ok) throw new Error(`deliveries HTTP ${dl.status}`);
      const s = await st.json();
      const d = await dl.json();
      setConnStatus(s);
      setConnEnabled(!!s.enabled);
      // Do not put redacted host into the edit field (would overwrite real URL on save).
      setConnDeliveries(d.deliveries || []);
    } catch (e) {
      setConnMsg(String(e));
      setConnStatus(null);
      setConnDeliveries([]);
    } finally {
      setConnLoading(false);
    }
  }

  async function saveConnector() {
    setConnMsg(null);
    setConnSaving(true);
    try {
      const body = { enabled: !!connEnabled };
      // Only send webhook_url when the operator typed a new value (avoids
      // overwriting a configured URL with the redacted display form).
      if (connUrl.trim()) body.webhook_url = connUrl.trim();
      if (connSecret.trim()) body.shared_secret = connSecret.trim();
      const r = await fetch("/api/frontline/connectors/config", {
        method: "PUT",
        headers: {
          ...apiHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      setConnSecret("");
      setConnUrl("");
      setConnMsg("Connector config saved.");
      await loadConnector({ preserveMessage: true });
    } catch (e) {
      setConnMsg(String(e));
    } finally {
      setConnSaving(false);
    }
  }

  async function replayConnector(id) {
    setConnMsg(null);
    try {
      const r = await fetch(
        `/api/frontline/connectors/deliveries/${encodeURIComponent(id)}/replay`,
        { method: "POST", headers: apiHeaders() }
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      setConnMsg(`Replayed delivery ${id}`);
      await loadConnector({ preserveMessage: true });
    } catch (e) {
      setConnMsg(String(e));
    }
  }

  useEffect(() => {
    load();
    loadDeadLetters();
    loadConnector();
  }, []);

  useEffect(() => {
    let live = true;
    fetch("/health", { headers: apiHeaders() })
      .then((r) => (r.ok ? r.json() : {}))
      .then((d) => {
        if (!live) return;
        setAuthRequired(typeof d.auth_required === "boolean" ? d.auth_required : null);
        setSingleWorker(d.single_worker);
        if (d.alert_webhook_url) setAlertWebhook(d.alert_webhook_url);
        else setAlertWebhook("Managed on server");
      })
      .catch(() => {
        if (!live) return;
        setAuthRequired(null);
        setAlertWebhook("Status unavailable");
      });
    return () => { live = false; };
  }, [statusRefresh]);

  function refreshGeneral() {
    load();
    loadDeadLetters();
    loadConnector();
    setStatusRefresh((value) => value + 1);
  }

  function saveApiKey() {
    // Centralized credential handling: sync the live input into the store
    // first so saved requests use exactly what the operator typed.
    storeApiKey(apiKey.trim(), { remember: rememberKey });
    setApiKey(apiKey.trim());
    notifyAuthChange();
    // Reload pack list + ops surfaces that require the key when auth is on.
    refreshGeneral();
  }

  async function selectPack(packId) {
    if (packId === active) return;
    setSwitching(true);
    setError(null);
    try {
      const r = await fetch(
        `/api/packs/active?pack_id=${encodeURIComponent(packId)}`,
        {
          method: "PUT",
          headers: apiHeaders(),
        }
      );
      if (!r.ok) {
        const detail = await r.text();
        throw new Error(`HTTP ${r.status}: ${detail}`);
      }
      const d = await r.json();
      setActive(d.active);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSwitching(false);
    }
  }

  const activePack = packs.find((p) => p.id === active);

  // Exactly one of: not configured / configured / unknown. Never the key,
  // a prefix of it, or its length.
  const metaConfigured = !metaStatus?.unavailable && typeof metaStatus?.key_configured === "boolean"
    ? metaStatus.key_configured : null;
  const metaStatusLine = !metaStatus ? "Checking…" : metaConfigured === null
    ? "Status unknown" : metaConfigured ? "Configured" : "Not configured";

  async function runDemoTraffic() {
    setSimBusy(true);
    setSimMsg(null);
    try {
      const d = await simulateTraffic({ count: 15 });
      setSimMsg(`Seeded ${d.completed ?? 15} simulated contacts. They stay out of live metrics unless you check Include simulated on Early warning.`);
    } catch (e) {
      setSimMsg(String(e.message || e));
    } finally {
      setSimBusy(false);
    }
  }

  return (
    <div className="settings-page">
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="sub">Manage console access, domain packs and connections.</p>
        </div>
        {panel === "general" && (
          <button type="button" className="ghost" onClick={refreshGeneral} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        )}
      </header>

      <div className="tabs settings-tabs" role="tablist" aria-label="Settings panels">
        {[
          { id: "general", label: "General" },
          { id: "builder", label: "Pack builder" },
          { id: "lab", label: "Lab" },
        ].map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={panel === t.id}
            className={"tab" + (panel === t.id ? " active" : "")}
            onClick={() => patchHashQuery({ tab: t.id })}>
            {t.label}
          </button>
        ))}
      </div>

      {panel === "builder" && <PackBuilder embedded />}
      {panel === "lab" && <FeatureStudio embedded />}
      {panel === "general" && (
        <div className="settings-general">
          {error && (
            <Banner tone="error" onDismiss={() => setError(null)}>{error}</Banner>
          )}

          <div className="settings-grid settings-access-grid">
            <section className="panel settings-card" aria-labelledby="settings-api-title">
              <div className="settings-card-heading">
                <h2 id="settings-api-title">Pilot API key</h2>
                <span className="settings-status">
                  {authRequired === null ? "Status unknown" : authRequired ? "Key required" : "Open local"}
                </span>
              </div>
              <p className="settings-description">Access this console with your pilot key. The key is used only by this browser.</p>
              <div className="settings-key-row">
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Paste pilot API key" aria-label="Pilot API key" autoComplete="off" />
                <button type="button" className="primary" onClick={saveApiKey}>Save</button>
              </div>
              <label className="check-row settings-check">
                <input type="checkbox" checked={rememberKey} onChange={(e) => setRememberKey(e.target.checked)}
                  aria-label="Remember API key on this device" />
                Remember on this device
              </label>
              <p className="settings-help">Unchecked: keep the key in memory only.</p>
            </section>

            <section className="panel settings-card" aria-labelledby="settings-meta-title">
              <div className="settings-card-heading">
                <h2 id="settings-meta-title">Meta model key</h2>
                <span className={`settings-status ${metaConfigured === true ? "settings-status-ok" : ""}`} data-testid="meta-key-status">
                  <i aria-hidden="true" />{metaStatusLine}
                </span>
              </div>
              <p className="settings-description">Managed on the server. The Meta key enables AI models and should never be entered in the pilot key field.</p>
              <p className="settings-meta-note">
                {metaConfigured === true ? "A Meta key is configured on the server."
                  : metaConfigured === false ? "Add a server key to enable the Meta AI layer."
                  : "Refresh to check the server configuration."}
              </p>
              <details className="settings-disclosure settings-setup">
                <summary>Server setup instructions</summary>
                <ol>
                  <li>Open the repository’s <code>.env</code> file, or copy <code>.env.example</code> to <code>.env</code>.</li>
                  <li>Set <code>META_API_KEY</code> to your Meta key. Keep the pilot key separate; it controls console access.</li>
                  <li>Restart the API using your deployment command. For local development: <code className="settings-command">python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000</code></li>
                  <li>Refresh this page to check the configuration. Verify the connection with <code className="settings-command">python -m scripts.ai_meta_smoke</code></li>
                </ol>
                {singleWorker === true && <p className="settings-help">This server uses a single worker for its active-contact registry.</p>}
              </details>
            </section>
          </div>

          <section className="panel settings-card settings-packs" aria-labelledby="settings-packs-title">
            <div className="settings-card-heading">
              <div>
                <h2 id="settings-packs-title">Domain packs</h2>
                <p className="settings-description">Choose the domain used for new contacts and analysis.</p>
              </div>
              {active && <span className="settings-status settings-status-ok"><i aria-hidden="true" />{activePack?.display_name || active}</span>}
            </div>
            {loading ? <div className="settings-empty">Loading packs…</div> : (
              <div className="settings-table-scroll">
                <table className="settings-table">
                  <thead><tr><th scope="col">Pack</th><th scope="col">Version</th><th scope="col">Fields</th><th scope="col">Validation</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
                  <tbody>
                    {packs.filter((pack) => pack.id && !String(pack.id).startsWith("_") && !pack.error).map((pack) => (
                      <tr key={pack.id} className={pack.is_active ? "settings-active-pack" : ""}>
                        <td><strong>{pack.display_name || pack.id}</strong><span className="settings-secondary mono">{pack.id}</span></td>
                        <td className="mono settings-version">{pack.pack_version || "—"}</td>
                        <td><span className="settings-slot-list">{(pack.slots || []).slice(0, 4).join(", ") || "—"}</span>{(pack.slots || []).length > 4 && <span className="muted"> +{pack.slots.length - 4}</span>}</td>
                        <td><span className={pack.lint_errors?.length ? "settings-validation-error" : "settings-validation-ok"}>{pack.lint_errors?.length ? `${pack.lint_errors.length} issues` : "Clean"}</span></td>
                        <td className="settings-table-action">
                          {pack.is_active ? <span className="settings-current">Active</span> : (
                            <button type="button" className="ghost" disabled={switching || Boolean(pack.error) || Boolean(pack.lint_errors?.length)}
                              onClick={() => selectPack(pack.id)} title={pack.lint_errors?.length ? "Pack has validation errors" : `Activate ${pack.display_name || pack.id}`}>
                              Activate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!packs.length && !error && <div className="settings-empty">No domain packs available.</div>}
              </div>
            )}
          </section>

          <div className="settings-section-heading">
            <h2>Connections & alerts</h2>
            <span>Delivery settings and retries</span>
          </div>
          <div className="settings-grid settings-connections-grid">
            <section className="panel settings-card" aria-labelledby="settings-connector-title">
              <div className="settings-card-heading">
                <h2 id="settings-connector-title">Outbound connector</h2>
                <button type="button" className="settings-text-button" onClick={() => loadConnector()} disabled={connLoading || connSaving}>
                  {connLoading ? "Refreshing…" : "Refresh connector"}
                </button>
              </div>
              <p className="settings-description">Send case and investigation events to an HTTP webhook, or save them to the local outbox.</p>
              <label className="check-row settings-check settings-connector-switch">
                <input type="checkbox" checked={connEnabled} onChange={(e) => setConnEnabled(e.target.checked)} aria-label="Enable outbound connectors" />
                Enable outbound events
              </label>
              <div className="settings-field">
                <label htmlFor="settings-connector-url">Webhook URL <span className="settings-optional">optional</span></label>
                <input id="settings-connector-url" value={connUrl} onChange={(e) => setConnUrl(e.target.value)}
                  placeholder={connStatus?.webhook_url_redacted ? `Configured: ${connStatus.webhook_url_redacted}` : "https://hooks.example.com/tracex"}
                  aria-label="Connector webhook URL" />
                <p className="settings-help">Leave blank to keep the current URL. Without a URL, events go to the local outbox.</p>
              </div>
              <div className="settings-field">
                <label htmlFor="settings-connector-secret">Shared secret <span className="settings-optional">optional</span></label>
                <input id="settings-connector-secret" type="password" value={connSecret} onChange={(e) => setConnSecret(e.target.value)}
                  placeholder={connStatus?.shared_secret_set ? "Configured · enter to replace" : "Enter a shared secret"}
                  autoComplete="off" aria-label="Connector shared secret" />
              </div>
              <div className="settings-save-row">
                <button type="button" className="primary" onClick={saveConnector} disabled={connSaving || connLoading}>
                  {connSaving ? "Saving…" : "Save connector"}
                </button>
                {connStatus && <span className="settings-help">Destination: {connStatus.sink || "—"}</span>}
              </div>
              {connMsg && <Banner tone={bannerTone(connMsg)} onDismiss={() => setConnMsg(null)}>{connMsg}</Banner>}
              <details className="settings-disclosure settings-deliveries">
                <summary>Pending deliveries <span className="settings-count">{connLoading ? "…" : connStatus ? connDeliveries.length : "—"}</span></summary>
                <p className="settings-help">Up to 50 pending deliveries. Replay resends the stored event to its original destination.</p>
                {connStatus && <p className="settings-delivery-counts">{Object.entries(connStatus.delivery_counts || {}).map(([key, value]) => `${key}: ${value}`).join(" · ") || "No deliveries recorded."}</p>}
                {!connDeliveries.length && !connLoading && connStatus && <div className="settings-empty">No pending connector deliveries.</div>}
                {connDeliveries.length > 0 && <DeliveryTable rows={connDeliveries} kind="connector" onReplay={replayConnector} />}
              </details>
              <details className="settings-disclosure settings-technical">
                <summary>Connector details</summary>
                <p className="settings-help">The shared secret is sent as <code>X-Connector-Secret</code>. Local outbox files are stored in <code>data/connectors/outbox/</code>. This is a generic HTTP connector; dedicated Salesforce, ServiceNow and Twilio integrations are not included.</p>
              </details>
            </section>

            <section className="panel settings-card" aria-labelledby="settings-alerts-title">
              <div className="settings-card-heading">
                <h2 id="settings-alerts-title">Alerts</h2>
                <span className="settings-status">Server managed</span>
              </div>
              <p className="settings-description">Deliver operational alerts to your configured webhook.</p>
              <div className="settings-field">
                <label htmlFor="settings-alert-url">Alert webhook</label>
                <input id="settings-alert-url" value={alertWebhook} readOnly placeholder="Managed on server" aria-label="Alert webhook URL" />
                <p className="settings-help">Set the URL in the server environment and restart the API to apply changes.</p>
              </div>
              <div className="settings-alert-queue">
                <div className="settings-card-heading">
                  <h3>Failed deliveries</h3>
                  <button type="button" className="settings-text-button" onClick={() => loadDeadLetters()} disabled={dlLoading}>
                    {dlLoading ? "Refreshing…" : "Refresh alerts"}
                  </button>
                </div>
                <p className="settings-description">Slack and webhook alerts that exhausted their retries.</p>
                {dlMsg && <Banner tone={bannerTone(dlMsg)} onDismiss={() => setDlMsg(null)}>{dlMsg}</Banner>}
                {dlLoading && <div className="settings-empty">Loading failed alerts…</div>}
                {!deadLetters.length && !dlLoading && !(dlMsg && bannerTone(dlMsg) === "error") && (
                  <div className="settings-empty settings-empty-ok"><i aria-hidden="true" />No pending failed alerts.</div>
                )}
                {deadLetters.length > 0 && (
                  <details className="settings-disclosure settings-deliveries">
                    <summary>Review failed alerts <span className="settings-count">{deadLetters.length}</span></summary>
                    <p className="settings-help">Up to 50 pending alerts. Replay resends the stored payload to the original endpoint.</p>
                    <DeliveryTable rows={deadLetters} kind="alert" onReplay={replayDeadLetter} />
                  </details>
                )}
              </div>
            </section>
          </div>

          <section className="panel settings-card settings-demo" aria-labelledby="settings-demo-title">
            <div>
              <h2 id="settings-demo-title">Demo traffic</h2>
              <p className="settings-description">Replay 15 sample contacts. Live metrics include them only when test traffic is enabled in Early warning.</p>
            </div>
            <button type="button" className="ghost" onClick={runDemoTraffic} disabled={simBusy}>
              {simBusy ? "Seeding…" : "Seed 15 simulated contacts"}
            </button>
            {simMsg && <Banner tone={bannerTone(simMsg)} onDismiss={() => setSimMsg(null)}>{simMsg}</Banner>}
          </section>
        </div>
      )}
    </div>
  );
}

function DeliveryTable({ rows, kind, onReplay }) {
  const isAlert = kind === "alert";
  return (
    <div className="settings-table-scroll">
      <table className="settings-table settings-delivery-table">
        <thead><tr><th scope="col">Event / ID</th><th scope="col">Reference</th><th scope="col">{isAlert ? "Attempts" : "Destination"}</th><th scope="col">Error</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
        <tbody>{rows.map((row) => {
          const id = isAlert ? row.dead_letter_id : row.delivery_id;
          return (
            <tr key={id}>
              <td><strong>{row.event}</strong><span className="settings-secondary mono" title={id}>{id?.length > 18 ? `${id.slice(0, 18)}…` : id}</span></td>
              <td className="mono">{row.ref_id}</td>
              <td>{isAlert ? row.attempts : row.sink}</td>
              <td className="settings-error-cell" title={row.error || ""}>{(row.error || "—").slice(0, 80)}</td>
              <td><button type="button" className="ghost" onClick={() => onReplay(id)} aria-label={`Replay ${isAlert ? "alert" : "delivery"} ${id}`}>Replay</button></td>
            </tr>
          );
        })}</tbody>
      </table>
    </div>
  );
}
