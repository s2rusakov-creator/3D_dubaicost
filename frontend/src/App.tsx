import { useState } from "react";
import { BuildingCard } from "./components/BuildingCard/BuildingCard";
import { DistrictCard } from "./components/DistrictCard/DistrictCard";
import { InfoPanel } from "./components/InfoPanel/InfoPanel";
import { MapView } from "./components/Map/MapView";
import { MapLayerPanel } from "./components/MapLayerPanel/MapLayerPanel";
import { ReviewPanel } from "./components/ReviewPanel/ReviewPanel";

export default function App() {
  const [showInfo, setShowInfo] = useState(false);
  const [showReview, setShowReview] = useState(false);

  return (
    <div className="app">
      <MapView />
      <MapLayerPanel />
      <BuildingCard />
      <DistrictCard />

      <div className="corner-buttons">
        <button className="corner-btn" onClick={() => setShowInfo(true)}>
          About data
        </button>
        <button className="corner-btn corner-btn-dim" onClick={() => setShowReview(true)}>
          Admin
        </button>
      </div>

      {showInfo && <InfoPanel onClose={() => setShowInfo(false)} />}
      {showReview && <ReviewPanel onClose={() => setShowReview(false)} />}
    </div>
  );
}
