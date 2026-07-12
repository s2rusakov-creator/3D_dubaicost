import { useState } from "react";
import { BuildingCard } from "./components/BuildingCard/BuildingCard";
import { DistrictCard } from "./components/DistrictCard/DistrictCard";
import { InfoPanel } from "./components/InfoPanel/InfoPanel";
import { LanguageModal, LanguageSwitcher } from "./components/LanguageControls/LanguageControls";
import { MapView } from "./components/Map/MapView";
import { MapLayerPanel } from "./components/MapLayerPanel/MapLayerPanel";
import { useT } from "./i18n";
import { useAppStore } from "./store";

// Admin (match review queue) скрыт из UI — сейчас карта в основном на оценках
// (не реальных данных), модерация реального matching не актуальна для демо.
// Код/API (ReviewPanel, /api/review) не удалены — легко вернуть при переходе
// на живые данные.

export default function App() {
  const [showInfo, setShowInfo] = useState(false);
  const lang = useAppStore((s) => s.lang);
  const t = useT();

  return (
    <div className="app">
      <MapView />
      <LanguageSwitcher />
      <MapLayerPanel />
      <BuildingCard />
      <DistrictCard />

      <div className="corner-buttons">
        <button className="corner-btn" onClick={() => setShowInfo(true)}>
          {t("app.about")}
        </button>
      </div>

      {showInfo && <InfoPanel onClose={() => setShowInfo(false)} />}

      {lang === null && <LanguageModal />}
    </div>
  );
}
