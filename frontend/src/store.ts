import { create } from "zustand";
import { DEFAULT_LAYER_ID } from "./layers.config";

export interface DistrictInfo {
  name: string;
  dominant_community: string | null;
  communities: string | null;
  note: string | null;
  sources: string | null;
  is_indicative: boolean;
}

interface AppState {
  activeLayerId: string;
  setActiveLayer: (id: string) => void;
  selectedBuildingId: number | null;
  setSelectedBuilding: (id: number | null) => void;

  // Оверлеи (независимы от радио-слоёв зданий)
  showDemographics: boolean;
  toggleDemographics: () => void;
  showPois: boolean;
  togglePois: () => void;
  selectedDistrict: DistrictInfo | null;
  setSelectedDistrict: (d: DistrictInfo | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeLayerId: DEFAULT_LAYER_ID,
  setActiveLayer: (id) => set({ activeLayerId: id }),
  selectedBuildingId: null,
  setSelectedBuilding: (id) => set({ selectedBuildingId: id }),

  showDemographics: false,
  toggleDemographics: () => set((s) => ({ showDemographics: !s.showDemographics })),
  showPois: false,
  togglePois: () => set((s) => ({ showPois: !s.showPois })),
  selectedDistrict: null,
  setSelectedDistrict: (d) => set({ selectedDistrict: d }),
}));
