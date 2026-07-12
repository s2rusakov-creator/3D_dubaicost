/**
 * Карточка демо-зоны: ориентировочные диаспоры района.
 * ВАЖНО: данные помечены как ориентировочные (не официальная статистика).
 */
import { districtDesc } from "../../districtI18n";
import { useT } from "../../i18n";
import { COMMUNITY_STYLES } from "../../overlays.config";
import { useAppStore } from "../../store";
import "../BuildingCard/BuildingCard.css";
import "./DistrictCard.css";

export function DistrictCard() {
  const t = useT();
  const lang = useAppStore((s) => s.lang) ?? "en";
  const district = useAppStore((s) => s.selectedDistrict);
  const setSelectedDistrict = useAppStore((s) => s.setSelectedDistrict);

  if (!district) return null;

  const communityKey = district.dominant_community;
  const community = communityKey ? COMMUNITY_STYLES[communityKey] : undefined;
  // Описания района — переводим по языку; фолбэк на текст из API (рус.)
  const desc = districtDesc(district.name, lang);
  const communitiesText = desc?.communities ?? district.communities;
  const noteText = desc?.note ?? district.note;

  return (
    <div className="district-card">
      <div className="card-header">
        <h2>{district.name}</h2>
        <button className="card-close" onClick={() => setSelectedDistrict(null)}>
          ✕
        </button>
      </div>

      {district.is_indicative && <div className="district-badge">{t("district.badge")}</div>}

      {community && communityKey && (
        <div className="card-row">
          <span className="swatch" style={{ background: community.color }} />
          <span className="card-value">{t(`community.${communityKey}`)}</span>
        </div>
      )}

      {communitiesText && (
        <div className="card-section">
          <div className="card-section-title">{t("district.who_lives")}</div>
          <div className="district-text">{communitiesText}</div>
        </div>
      )}

      {noteText && <div className="district-text district-note">{noteText}</div>}

      {district.sources && (
        <div className="card-source">{t("district.sources")}: {district.sources}</div>
      )}
    </div>
  );
}
