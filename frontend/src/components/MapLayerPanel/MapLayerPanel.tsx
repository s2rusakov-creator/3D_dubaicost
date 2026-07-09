/**
 * Панель слоёв в стиле UrbanCost: заголовок "Map Layer", градиент-легенда
 * активного слоя с порогами, список слоёв с toggle (активен ровно один),
 * и отдельная секция независимых оверлеев (демография, POI).
 */
import { useState } from "react";
import { LAYERS } from "../../layers.config";
import { COMMUNITY_STYLES, POI_STYLES } from "../../overlays.config";
import { useAppStore } from "../../store";
import "./MapLayerPanel.css";

function formatThreshold(value: number): string {
  return value >= 1000 ? value.toLocaleString("en-US") : String(value);
}

export function MapLayerPanel() {
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
        <span>Map Layer</span>
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
            <div className="legend-unit">{active.unit}</div>
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
                    <span className="layer-title">{layer.title}</span>
                    <span className={`toggle ${isActive ? "on" : ""}`}>
                      <span className="toggle-knob" />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="overlay-section">
            <div className="overlay-title">Оверлеи</div>
            <ul className="layer-list">
              <li>
                <button
                  className={`layer-item ${showDemographics ? "active" : ""}`}
                  onClick={toggleDemographics}
                >
                  <span className="layer-icon">👥</span>
                  <span className="layer-title">Диаспоры по районам</span>
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
                  <span className="layer-title">Достопримечательности</span>
                  <span className={`toggle ${showPois ? "on" : ""}`}>
                    <span className="toggle-knob" />
                  </span>
                </button>
              </li>
            </ul>

            {showDemographics && (
              <div className="overlay-legend">
                {Object.values(COMMUNITY_STYLES).map((s) => (
                  <div className="overlay-legend-row" key={s.label}>
                    <span className="swatch" style={{ background: s.color }} />
                    <span>{s.label}</span>
                  </div>
                ))}
                <div className="overlay-disclaimer">
                  Ориентировочно, по открытым источникам — не официальная статистика
                </div>
              </div>
            )}

            {showPois && (
              <div className="overlay-legend">
                {Object.values(POI_STYLES).map((s) => (
                  <div className="overlay-legend-row" key={s.label}>
                    <span className="swatch swatch-round" style={{ background: s.color }} />
                    <span>{s.label}</span>
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
