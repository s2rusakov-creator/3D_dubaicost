/** Карточка здания: атрибуты, метрики и явное состояние "No data" для отсутствующих. */
import { useEffect, useState } from "react";
import { useT } from "../../i18n";
import { useAppStore } from "../../store";
import "./BuildingCard.css";

interface MetricPoint {
  period: string;
  median: number | null;
  mean: number | null;
  sample_size: number | null;
}

interface BuildingDetail {
  building: {
    id: number;
    name: string | null;
    district: string | null;
    master_project: string | null;
    built_year: number | null;
    floors: number | null;
    units_count: number | null;
    parking_ratio: number | null;
    cooling_provider: string | null;
    geo_source: string | null;
  };
  metrics: Record<string, MetricPoint[]>;
  service_charge: { year: number; rate_aed_sqft: number; source: string | null } | null;
  cooling_tariff: { provider: string; source_note: string } | null;
}

function latest(points?: MetricPoint[]): MetricPoint | null {
  return points && points.length > 0 ? points[points.length - 1] : null;
}

function Row({ label, value, unit }: { label: string; value: string | number | null; unit?: string }) {
  const t = useT();
  return (
    <div className="card-row">
      <span className="card-label">{label}</span>
      {value === null || value === undefined ? (
        <span className="card-nodata">{t("card.no_data")}</span>
      ) : (
        <span className="card-value">
          {typeof value === "number" ? value.toLocaleString("en-US", { maximumFractionDigits: 1 }) : value}
          {unit ? ` ${unit}` : ""}
        </span>
      )}
    </div>
  );
}

export function BuildingCard() {
  const t = useT();
  const buildingId = useAppStore((s) => s.selectedBuildingId);
  const setSelectedBuilding = useAppStore((s) => s.setSelectedBuilding);
  const [detail, setDetail] = useState<BuildingDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (buildingId === null) {
      setDetail(null);
      return;
    }
    setLoading(true);
    fetch(`/api/buildings/${buildingId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [buildingId]);

  if (buildingId === null) return null;

  const price = latest(detail?.metrics["price_sqft"]);
  const rent = latest(detail?.metrics["rent_sqft"]);
  const cooling = latest(detail?.metrics["cooling_est"]);

  // Истинная стоимость владения: обязательные годовые расходы на sqft.
  // Считаем только из имеющихся компонент; если нет ни одной — "No data".
  const scRate = detail?.service_charge?.rate_aed_sqft ?? null;
  const coolingRate = cooling?.median ?? null;
  const runningPerSqft =
    scRate === null && coolingRate === null
      ? null
      : (scRate ?? 0) + (coolingRate ?? 0);
  const EXAMPLE_SQFT = 1000;

  return (
    <div className="building-card">
      <div className="card-header">
        <h2>{detail?.building.name ?? `Building #${buildingId}`}</h2>
        <button className="card-close" onClick={() => setSelectedBuilding(null)}>
          ✕
        </button>
      </div>

      {loading && <div className="card-loading">{t("card.loading")}</div>}

      {detail && (
        <>
          <div className="card-subtitle">
            {[detail.building.district, detail.building.master_project]
              .filter(Boolean)
              .join(" · ") || "—"}
          </div>

          <div className="card-section">
            <Row label={t("card.price")} value={price?.median ?? null} unit={t("u.aed_sqft")} />
            <Row label={t("card.rent")} value={rent?.median ?? null} unit={t("u.aed_sqft_yr")} />
            <Row
              label={t("card.service_charge")}
              value={detail.service_charge?.rate_aed_sqft ?? null}
              unit={detail.service_charge ? `${t("u.aed_sqft_yr")} (${detail.service_charge.year})` : undefined}
            />
            <Row label={t("card.cooling")} value={coolingRate} unit={t("u.aed_sqft_yr")} />
            <Row
              label={t("card.cooling_provider")}
              value={detail.cooling_tariff?.provider ?? detail.building.cooling_provider}
            />
          </div>

          <div className="card-section true-cost">
            <div className="card-section-title">{t("card.true_cost")}</div>
            <Row label={t("card.running_costs")} value={runningPerSqft} unit={t("u.aed_sqft_yr")} />
            {runningPerSqft !== null && (
              <>
                <Row
                  label={`${t("card.example")} ${EXAMPLE_SQFT.toLocaleString()} ${t("u.sqft")} ${t("card.per_year")}`}
                  value={runningPerSqft * EXAMPLE_SQFT}
                  unit="AED"
                />
                <Row
                  label={`${t("card.example")} ${EXAMPLE_SQFT.toLocaleString()} ${t("u.sqft")} ${t("card.per_month")}`}
                  value={(runningPerSqft * EXAMPLE_SQFT) / 12}
                  unit="AED"
                />
              </>
            )}
            {coolingRate !== null && <div className="card-source">{t("card.cooling_note")}</div>}
          </div>

          <div className="card-section">
            <Row label={t("card.built_year")} value={detail.building.built_year} />
            <Row label={t("card.floors")} value={detail.building.floors} />
            <Row label={t("card.units")} value={detail.building.units_count} />
            <Row label={t("card.parking")} value={detail.building.parking_ratio} />
          </div>

          {price?.sample_size != null && (
            <div className="card-source">
              {t("card.sales_sample")}: {price.sample_size} tx · {price.period}
            </div>
          )}
          {detail.building.geo_source && (
            <div className="card-source">{t("card.geometry")}: {detail.building.geo_source}</div>
          )}
        </>
      )}
    </div>
  );
}
