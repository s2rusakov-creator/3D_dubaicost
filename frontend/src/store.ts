import { create } from "zustand";
import { DEFAULT_LAYER_ID } from "./layers.config";

export type Lang = "ru" | "en" | "es";

function initialLang(): Lang | null {
  if (typeof localStorage === "undefined") return null;
  const v = localStorage.getItem("lang");
  return v === "ru" || v === "en" || v === "es" ? v : null; // null => показать выбор языка
}

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

  // Язык интерфейса (null = ещё не выбран, показываем модалку выбора)
  lang: Lang | null;
  setLang: (l: Lang) => void;
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

  lang: initialLang(),
  setLang: (l) => {
    try {
      localStorage.setItem("lang", l);
    } catch {
      // приватный режим — просто держим в памяти
    }
    set({ lang: l });
  },
}));
