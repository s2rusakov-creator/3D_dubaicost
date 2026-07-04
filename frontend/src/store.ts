import { create } from "zustand";
import { DEFAULT_LAYER_ID } from "./layers.config";

interface AppState {
  activeLayerId: string;
  setActiveLayer: (id: string) => void;
  selectedBuildingId: number | null;
  setSelectedBuilding: (id: number | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeLayerId: DEFAULT_LAYER_ID,
  setActiveLayer: (id) => set({ activeLayerId: id }),
  selectedBuildingId: null,
  setSelectedBuilding: (id) => set({ selectedBuildingId: id }),
}));
