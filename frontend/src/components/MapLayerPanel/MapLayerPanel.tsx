/**
 * Панель слоёв в стиле UrbanCost: заголовок "Map Layer", градиент-легенда
 * активного слоя с порогами, список слоёв с toggle (активен ровно один),
 * и отдельная секция независимых оверлеев (демография, POI).
 */
import { useState } from "react";
import { useT } from "../../i18n";
import { LAYERS } from "../../layers.config";
import { COMMUNITY_STYLES, POI_STYLES } from "../../overlays.config";
import { useAppStore } from "../../store";
import "./MapLayerPanel.css";

function formatThreshold(value: number): string {
  return value >= 1000 ? value.toLocaleString("en-US") : String(value);
}

export function MapLayerPanel() {
  const t = useT();
  const [collapsed, setCollapsed] = useState(false);
  const activeLayerId = useAppStore((s) => s.activeLayerId);
  const setActiveLayer = useAppStore((s) => s.setActiveLayer);
  const showDemographics = useAppStore((s) => s.showDemographics);
  const toggleDemographics = useAppStore((s) => s.toggleDemographics);
  const showPois = useAppStore((s) => s.showPois);
  const togglePois = useAppStore((s) => s.togglePois);
  const active = LAYERS.find((l) => l.id === activeLayerId) ?? LAYERS[0];

  const gradient = `linear-gradient(to right, ${active.colors.join(", ")})`;

  return (
    <div className="layer-panel">
      <button className="layer-panel-header" onClick={() => setCollapsed(!collapsed)}>
        <span>{t("panel.title")}</span>
        <span className={`chevron ${collapsed ? "up" : ""}`}>▾</span>
      </button>

      {!collapsed && (
        <>
          <div className="legend">
            <div className="legend-gradient" style={{ background: gradient }} />
            <div className="legend-labels">
              {active.thresholds.map((t, i) => (
                <span key={t}>
                  {formatThreshold(t)}
                  {i === active.thresholds.length - 1 ? "+" : ""}
                </span>
              ))}
            </div>
            <div className="legend-unit">{t(`unit.${active.id}`)}</div>
          </div>

          <ul className="layer-list">
            {LAYERS.map((layer) => {
              const isActive = layer.id === active.id;
              return (
                <li key={layer.id}>
                  <button
                    className={`layer-item ${isActive ? "active" : ""}`}
                    onClick={() => setActiveLayer(layer.id)}
                  >
                    <span className="layer-icon">{layer.icon}</span>
                    <span className="layer-title">{t(`layer.${layer.id}`)}</span>
                    <span className={`toggle ${isActive ? "on" : ""}`}>
                      <span className="toggle-knob" />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="overlay-section">
            <div className="overlay-title">{t("panel.overlays")}</div>
            <ul className="layer-list">
              <li>
                <button
                  className={`layer-item ${showDemographics ? "active" : ""}`}
                  onClick={toggleDemographics}
                >
                  <span className="layer-icon">👥</span>
                  <span className="layer-title">{t("overlay.demographics")}</span>
                  <span className={`toggle ${showDemographics ? "on" : ""}`}>
                    <span className="toggle-knob" />
                  </span>
                </button>
              </li>
              <li>
                <button
                  className={`layer-item ${showPois ? "active" : ""}`}
                  onClick={togglePois}
                >
                  <span className="layer-icon">📍</span>
                  <span className="layer-title">{t("overlay.pois")}</span>
                  <span className={`toggle ${showPois ? "on" : ""}`}>
                    <span className="toggle-knob" />
                  </span>
                </button>
              </li>
            </ul>

            {showDemographics && (
              <div className="overlay-legend">
                {Object.entries(COMMUNITY_STYLES).map(([key, s]) => (
                  <div className="overlay-legend-row" key={key}>
                    <span className="swatch" style={{ background: s.color }} />
                    <span>{t(`community.${key}`)}</span>
                  </div>
                ))}
                <div className="overlay-disclaimer">{t("disclaimer.demographics")}</div>
              </div>
            )}

            {showPois && (
              <div className="overlay-legend">
                {Object.entries(POI_STYLES).map(([key, s]) => (
                  <div className="overlay-legend-row" key={key}>
                    <span className="swatch swatch-round" style={{ background: s.color }} />
                    <span>{t(`poi.${key}`)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
