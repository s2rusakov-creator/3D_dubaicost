/** Страница "О данных": источники, покрытие по слоям, статус ETL. */
import { useEffect, useState } from "react";
import { LAYERS } from "../../layers.config";
import "./InfoPanel.css";

interface LayerCoverage {
  id: string;
  unit: string;
  buildings_covered: number;
  buildings_total: number;
}

interface SourceRun {
  source: string;
  last_run: string;
  status: string;
  rows_upserted: number | null;
  error: string | null;
}

const DATA_SOURCES = [
  {
    name: "DLD Transactions (Dubai Pulse)",
    url: "https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open",
    what: "Sales transactions",
  },
  {
    name: "DLD Rent Contracts (Dubai Pulse)",
    url: "https://www.dubaipulse.gov.ae/data/dld-registration/dld_rent_contracts-open",
    what: "Ejari rent contracts",
  },
  {
    name: "DLD Service Charge Index (Mollak)",
    url: "https://dubailand.gov.ae/en/eservices/service-charge-index-overview/",
    what: "Service charges, manual ingestion",
  },
  {
    name: "Empower / Tabreed",
    url: "https://www.empower.ae/customer-care/charges-explanation/",
    what: "District cooling tariffs (estimates)",
  },
  {
    name: "OpenStreetMap / Overture Maps",
    url: "https://www.openstreetmap.org",
    what: "Building footprints & heights",
  },
];

export function InfoPanel({ onClose }: { onClose: () => void }) {
  const [coverage, setCoverage] = useState<LayerCoverage[]>([]);
  const [sources, setSources] = useState<SourceRun[]>([]);

  useEffect(() => {
    fetch("/api/layers")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setCoverage(d.layers))
      .catch(() => undefined);
    fetch("/api/coverage")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setSources(d.sources))
      .catch(() => undefined);
  }, []);

  return (
    <div className="info-overlay" onClick={onClose}>
      <div className="info-panel" onClick={(e) => e.stopPropagation()}>
        <div className="info-header">
          <h2>About the data</h2>
          <button className="card-close" onClick={onClose}>✕</button>
        </div>

        <p className="info-note">
          DubaiCost shows the <b>true cost</b> of Dubai real estate: transaction
          prices plus mandatory running costs (service charge, district
          cooling). Grey buildings = no data for the selected layer — we never
          show a missing value as zero. Cooling fees are <b>estimates</b> based
          on published tariffs and industry assumptions.
        </p>

        <h3>Sources</h3>
        <ul className="info-sources">
          {DATA_SOURCES.map((s) => (
            <li key={s.name}>
              <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a>
              <span> — {s.what}</span>
            </li>
          ))}
        </ul>

        <h3>Coverage by layer</h3>
        <table className="info-table">
          <thead>
            <tr><th>Layer</th><th>Buildings covered</th></tr>
          </thead>
          <tbody>
            {coverage.map((c) => {
              const def = LAYERS.find((l) => l.id === c.id);
              return (
                <tr key={c.id}>
                  <td>{def?.title ?? c.id}</td>
                  <td>
                    {c.buildings_covered.toLocaleString()} /{" "}
                    {c.buildings_total.toLocaleString()}
                  </td>
                </tr>
              );
            })}
            {coverage.length === 0 && (
              <tr><td colSpan={2} className="card-nodata">API unavailable</td></tr>
            )}
          </tbody>
        </table>

        <h3>Last ETL runs</h3>
        <table className="info-table">
          <thead>
            <tr><th>Source</th><th>Status</th><th>Rows</th><th>When</th></tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.source}>
                <td>{s.source}</td>
                <td className={s.status === "failed" ? "status-failed" : "status-ok"}>
                  {s.status}
                </td>
                <td>{s.rows_upserted?.toLocaleString() ?? "—"}</td>
                <td>{s.last_run.slice(0, 16).replace("T", " ")}</td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr><td colSpan={4} className="card-nodata">No runs yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
