/**
 * Конфигурация оверлеев (демография, POI) — независимы от радио-слоёв зданий.
 */

/** Нейтральные приглушённые цвета категорий диаспор (не связаны с этносом). */
export interface CommunityStyle {
  color: string;
  label: string;
}

export const COMMUNITY_STYLES: Record<string, CommunityStyle> = {
  south_asian: { color: "#6b8e9e", label: "Южная Азия (индийцы, пакистанцы, иранцы)" },
  filipino_chinese_mixed: { color: "#9e8a6b", label: "Филиппинцы, китайцы, смешанные" },
  western_russian_expats: { color: "#7d8e6b", label: "Западные и русскоязычные экспаты" },
  emirati_affluent: { color: "#8e6b8a", label: "Граждане ОАЭ и состоятельные экспаты" },
};

export const DEFAULT_COMMUNITY_COLOR = "#5a5f6a";

/** Категории POI: цвет маркера-«шарика» + подпись легенды. */
export const POI_STYLES: Record<string, { color: string; label: string }> = {
  attraction: { color: "#e8a33d", label: "Достопримечательность" },
  mall: { color: "#5aa9e6", label: "Молл" },
  park: { color: "#6bbf59", label: "Парк" },
  beach: { color: "#e6c84f", label: "Пляж" },
  metro: { color: "#c77dff", label: "Метро" },
};

export const POI_DEFAULT_COLOR = "#9aa0aa";
