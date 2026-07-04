/**
 * Единый источник конфигурации слоёв карты.
 * Добавление нового слоя = добавление записи сюда (панель и карта подхватят сами).
 * id должен совпадать с параметром ?layer= бэкенда.
 */
export interface LayerDef {
  id: string;
  title: string;
  icon: string;
  unit: string;
  /** Пороговые значения легенды (по возрастанию), последний рисуется как "N+" */
  thresholds: number[];
  /** Цвета ступеней: colors.length === thresholds.length + 1 */
  colors: string[];
}

export const NO_DATA_COLOR = "#3a3f4a";

export const LAYERS: LayerDef[] = [
  {
    id: "price_sqft",
    title: "Price (per sqft)",
    icon: "💰",
    unit: "AED/sqft",
    thresholds: [500, 1000, 1500, 2000, 2500],
    colors: ["#12b886", "#74c476", "#ffd43b", "#ff922b", "#f03e3e", "#c2255c"],
  },
  {
    id: "rent_sqft",
    title: "Rent (per sqft / yr)",
    icon: "🔑",
    unit: "AED/sqft/yr",
    thresholds: [50, 80, 110, 140, 170],
    colors: ["#12b886", "#74c476", "#ffd43b", "#ff922b", "#f03e3e", "#c2255c"],
  },
  {
    id: "service_charge",
    title: "Service Charge",
    icon: "🧾",
    unit: "AED/sqft/yr",
    thresholds: [8, 12, 16, 20, 24],
    colors: ["#12b886", "#74c476", "#ffd43b", "#ff922b", "#f03e3e", "#c2255c"],
  },
  {
    id: "cooling_est",
    title: "District Cooling Fee",
    icon: "❄️",
    unit: "AED/sqft/yr",
    thresholds: [4, 8, 12, 16, 20],
    colors: ["#12b886", "#74c476", "#ffd43b", "#ff922b", "#f03e3e", "#c2255c"],
  },
  {
    id: "parking_ratio",
    title: "Parking Ratio",
    icon: "🚗",
    unit: "spaces/unit",
    thresholds: [0.5, 1.0, 1.5, 2.0, 2.5],
    colors: ["#c2255c", "#f03e3e", "#ff922b", "#ffd43b", "#74c476", "#12b886"],
  },
  {
    id: "built_year",
    title: "Built Year",
    icon: "🏗️",
    unit: "year",
    thresholds: [1995, 2005, 2010, 2015, 2020],
    colors: ["#4c6ef5", "#5c7cfa", "#748ffc", "#91a7ff", "#bac8ff", "#dbe4ff"],
  },
];

export const DEFAULT_LAYER_ID = "price_sqft";
