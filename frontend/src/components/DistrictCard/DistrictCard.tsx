/**
 * Карточка демо-зоны: ориентировочные диаспоры района.
 * ВАЖНО: данные помечены как ориентировочные (не официальная статистика).
 */
import { COMMUNITY_STYLES } from "../../overlays.config";
import { useAppStore } from "../../store";
import "../BuildingCard/BuildingCard.css";
import "./DistrictCard.css";

export function DistrictCard() {
  const district = useAppStore((s) => s.selectedDistrict);
  const setSelectedDistrict = useAppStore((s) => s.setSelectedDistrict);

  if (!district) return null;

  const community = district.dominant_community
    ? COMMUNITY_STYLES[district.dominant_community]
    : undefined;

  return (
    <div className="district-card">
      <div className="card-header">
        <h2>{district.name}</h2>
        <button className="card-close" onClick={() => setSelectedDistrict(null)}>
          ✕
        </button>
      </div>

      {district.is_indicative && (
        <div className="district-badge">Ориентировочно · не офиц. статистика</div>
      )}

      {community && (
        <div className="card-row">
          <span className="swatch" style={{ background: community.color }} />
          <span className="card-value">{community.label}</span>
        </div>
      )}

      {district.communities && (
        <div className="card-section">
          <div className="card-section-title">Кто преимущественно живёт</div>
          <div className="district-text">{district.communities}</div>
        </div>
      )}

      {district.note && <div className="district-text district-note">{district.note}</div>}

      {district.sources && (
        <div className="card-source">Источники: {district.sources}</div>
      )}
    </div>
  );
}
