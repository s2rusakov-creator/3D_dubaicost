/** Простой i18n: словари RU/EN/ES + хук useT(). Ключи стабильны, значения по языкам. */
import { useAppStore, type Lang } from "./store";

export const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: "ru", label: "Русский", short: "РУ" },
  { code: "en", label: "English", short: "EN" },
  { code: "es", label: "Español", short: "ES" },
];

type Dict = Record<Lang, string>;

export const TR: Record<string, Dict> = {
  // Панель слоёв
  "panel.title": { ru: "Слои карты", en: "Map Layer", es: "Capas del mapa" },
  "panel.overlays": { ru: "Оверлеи", en: "Overlays", es: "Superposiciones" },
  "overlay.demographics": { ru: "Диаспоры по районам", en: "Diasporas by district", es: "Diásporas por distrito" },
  "overlay.pois": { ru: "Достопримечательности", en: "Attractions", es: "Atracciones" },
  "disclaimer.demographics": {
    ru: "Ориентировочно, по открытым источникам — не официальная статистика",
    en: "Indicative, from open sources — not official statistics",
    es: "Indicativo, de fuentes abiertas — no es estadística oficial",
  },
  // Слои (по id)
  "layer.price_sqft": { ru: "Цена (за фут²)", en: "Price (per sqft)", es: "Precio (por pie²)" },
  "layer.rent_sqft": { ru: "Аренда (за фут²/год)", en: "Rent (per sqft / yr)", es: "Alquiler (por pie²/año)" },
  "layer.service_charge": { ru: "Сервисный сбор", en: "Service Charge", es: "Cargo de servicio" },
  "layer.cooling_est": { ru: "Плата за охлаждение", en: "District Cooling Fee", es: "Tarifa de refrigeración" },
  "layer.parking_ratio": { ru: "Парковка", en: "Parking Ratio", es: "Estacionamiento" },
  "layer.built_year": { ru: "Год постройки", en: "Built Year", es: "Año de construcción" },
  // Квадратный фут: sqft непонятен русско-/испаноязычным — локализуем (фут² / pie²)
  "u.sqft": { ru: "фут²", en: "sqft", es: "pie²" },
  "u.aed_sqft": { ru: "AED/фут²", en: "AED/sqft", es: "AED/pie²" },
  "u.aed_sqft_yr": { ru: "AED/фут²/год", en: "AED/sqft/yr", es: "AED/pie²/año" },
  // Единицы легенды (по id слоя)
  "unit.price_sqft": { ru: "AED/фут²", en: "AED/sqft", es: "AED/pie²" },
  "unit.rent_sqft": { ru: "AED/фут²/год", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.service_charge": { ru: "AED/фут²/год", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.cooling_est": { ru: "AED/фут²/год", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.parking_ratio": { ru: "мест/юнит", en: "spaces/unit", es: "plazas/unidad" },
  "unit.built_year": { ru: "год", en: "year", es: "año" },
  // Категории диаспор (по ключу)
  "community.south_asian": {
    ru: "Южная Азия (индийцы, пакистанцы, иранцы)",
    en: "South Asia (Indians, Pakistanis, Iranians)",
    es: "Asia del Sur (indios, pakistaníes, iraníes)",
  },
  "community.filipino_chinese_mixed": {
    ru: "Филиппинцы, китайцы, смешанные",
    en: "Filipinos, Chinese, mixed",
    es: "Filipinos, chinos, mixtos",
  },
  "community.western_russian_expats": {
    ru: "Западные и русскоязычные экспаты",
    en: "Western & Russian-speaking expats",
    es: "Expatriados occidentales y rusohablantes",
  },
  "community.emirati_affluent": {
    ru: "Граждане ОАЭ и состоятельные экспаты",
    en: "Emiratis & affluent expats",
    es: "Emiratíes y expatriados acomodados",
  },
  "community.mixed_diverse": {
    ru: "Смешанные (многонациональные районы)",
    en: "Mixed (multinational areas)",
    es: "Mixtos (áreas multinacionales)",
  },
  // POI (по ключу)
  "poi.attraction": { ru: "Достопримечательность", en: "Attraction", es: "Atracción" },
  "poi.mall": { ru: "Молл", en: "Mall", es: "Centro comercial" },
  "poi.park": { ru: "Парк", en: "Park", es: "Parque" },
  "poi.beach": { ru: "Пляж", en: "Beach", es: "Playa" },
  "poi.metro": { ru: "Метро", en: "Metro", es: "Metro" },
  // Карточка здания
  "card.price": { ru: "Цена", en: "Price", es: "Precio" },
  "card.rent": { ru: "Аренда", en: "Rent", es: "Alquiler" },
  "card.service_charge": { ru: "Сервисный сбор", en: "Service Charge", es: "Cargo de servicio" },
  "card.cooling": { ru: "Охлаждение (оц.)", en: "Cooling (est.)", es: "Refrigeración (est.)" },
  "card.cooling_provider": { ru: "Провайдер охлаждения", en: "Cooling provider", es: "Proveedor de refrigeración" },
  "card.true_cost": { ru: "Истинная стоимость владения (оц.)", en: "True cost of ownership (est.)", es: "Costo real de propiedad (est.)" },
  "card.running_costs": { ru: "Годовые расходы", en: "Running costs", es: "Costos anuales" },
  "card.built_year": { ru: "Год постройки", en: "Built Year", es: "Año de construcción" },
  "card.floors": { ru: "Этажей", en: "Floors", es: "Pisos" },
  "card.units": { ru: "Юнитов", en: "Units", es: "Unidades" },
  "card.parking": { ru: "Парковка", en: "Parking Ratio", es: "Estacionamiento" },
  "card.no_data": { ru: "Нет данных", en: "No data", es: "Sin datos" },
  "card.loading": { ru: "Загрузка…", en: "Loading…", es: "Cargando…" },
  "card.cooling_note": {
    ru: "Охлаждение — оценка по опубликованным тарифам, не счёт",
    en: "Cooling is an estimate from published tariffs, not a bill",
    es: "La refrigeración es una estimación de tarifas publicadas, no una factura",
  },
  "card.geometry": { ru: "Геометрия", en: "Geometry", es: "Geometría" },
  "card.sales_sample": { ru: "Выборка сделок", en: "Sales sample", es: "Muestra de ventas" },
  "card.example": { ru: "Пример", en: "Example", es: "Ejemplo" },
  "card.per_year": { ru: "в год", en: "/ yr", es: "/ año" },
  "card.per_month": { ru: "в мес", en: "/ mo", es: "/ mes" },
  // Карточка района
  "district.badge": { ru: "Ориентировочно · не офиц. статистика", en: "Indicative · not official statistics", es: "Indicativo · no oficial" },
  "district.who_lives": { ru: "Кто преимущественно живёт", en: "Who mostly lives here", es: "Quién vive principalmente" },
  "district.sources": { ru: "Источники", en: "Sources", es: "Fuentes" },
  // Кнопки
  "app.about": { ru: "О данных", en: "About data", es: "Sobre los datos" },
  "app.admin": { ru: "Админ", en: "Admin", es: "Admin" },
  // Модалка выбора языка
  "lang.choose": { ru: "Выберите язык", en: "Choose your language", es: "Elige tu idioma" },
  "lang.subtitle": {
    ru: "Можно сменить в любой момент — в правом верхнем углу",
    en: "You can change it anytime — top-right corner",
    es: "Puedes cambiarlo en cualquier momento — arriba a la derecha",
  },
};

export function tr(key: string, lang: Lang): string {
  return TR[key]?.[lang] ?? key;
}

/** Хук: возвращает функцию перевода t(key). Реагирует на смену языка в store. */
export function useT(): (key: string) => string {
  const lang = useAppStore((s) => s.lang) ?? "ru";
  return (key: string) => tr(key, lang);
}
