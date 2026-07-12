/** Простой i18n: словари AR/EN/ES + хук useT(). Ключи стабильны, значения по языкам. */
import { useAppStore, type Lang } from "./store";

export const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: "ar", label: "العربية", short: "ع" },
  { code: "en", label: "English", short: "EN" },
  { code: "es", label: "Español", short: "ES" },
];

type Dict = Record<Lang, string>;

export const TR: Record<string, Dict> = {
  // Панель слоёв
  "panel.title": { ar: "طبقات الخريطة", en: "Map Layer", es: "Capas del mapa" },
  "panel.overlays": { ar: "طبقات إضافية", en: "Overlays", es: "Superposiciones" },
  "overlay.demographics": { ar: "الجاليات حسب المنطقة", en: "Diasporas by district", es: "Diásporas por distrito" },
  "overlay.pois": { ar: "المعالم", en: "Attractions", es: "Atracciones" },
  "disclaimer.demographics": {
    ar: "تقديري، من مصادر مفتوحة — ليست إحصاءات رسمية",
    en: "Indicative, from open sources — not official statistics",
    es: "Indicativo, de fuentes abiertas — no es estadística oficial",
  },
  // Слои (по id)
  "layer.price_sqft": { ar: "السعر (لكل قدم²)", en: "Price (per sqft)", es: "Precio (por pie²)" },
  "layer.rent_sqft": { ar: "الإيجار (لكل قدم²/سنة)", en: "Rent (per sqft / yr)", es: "Alquiler (por pie²/año)" },
  "layer.service_charge": { ar: "رسوم الخدمة", en: "Service Charge", es: "Cargo de servicio" },
  "layer.cooling_est": { ar: "رسوم التبريد", en: "District Cooling Fee", es: "Tarifa de refrigeración" },
  "layer.parking_ratio": { ar: "مواقف السيارات", en: "Parking Ratio", es: "Estacionamiento" },
  "layer.built_year": { ar: "سنة البناء", en: "Built Year", es: "Año de construcción" },
  // Квадратный фут локализуем (قدم² / pie²)
  "u.sqft": { ar: "قدم²", en: "sqft", es: "pie²" },
  "u.aed_sqft": { ar: "درهم/قدم²", en: "AED/sqft", es: "AED/pie²" },
  "u.aed_sqft_yr": { ar: "درهم/قدم²/سنة", en: "AED/sqft/yr", es: "AED/pie²/año" },
  // Единицы легенды (по id слоя)
  "unit.price_sqft": { ar: "درهم/قدم²", en: "AED/sqft", es: "AED/pie²" },
  "unit.rent_sqft": { ar: "درهم/قدم²/سنة", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.service_charge": { ar: "درهم/قدم²/سنة", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.cooling_est": { ar: "درهم/قدم²/سنة", en: "AED/sqft/yr", es: "AED/pie²/año" },
  "unit.parking_ratio": { ar: "موقف/وحدة", en: "spaces/unit", es: "plazas/unidad" },
  "unit.built_year": { ar: "سنة", en: "year", es: "año" },
  // Категории диаспор (по ключу)
  "community.south_asian": {
    ar: "جنوب آسيا (هنود، باكستانيون، إيرانيون)",
    en: "South Asia (Indians, Pakistanis, Iranians)",
    es: "Asia del Sur (indios, pakistaníes, iraníes)",
  },
  "community.filipino_chinese_mixed": {
    ar: "فلبينيون، صينيون، مختلطون",
    en: "Filipinos, Chinese, mixed",
    es: "Filipinos, chinos, mixtos",
  },
  "community.western_russian_expats": {
    ar: "وافدون غربيون وناطقون بالروسية",
    en: "Western & Russian-speaking expats",
    es: "Expatriados occidentales y rusohablantes",
  },
  "community.emirati_affluent": {
    ar: "إماراتيون ووافدون ميسورون",
    en: "Emiratis & affluent expats",
    es: "Emiratíes y expatriados acomodados",
  },
  "community.mixed_diverse": {
    ar: "مختلط (مناطق متعددة الجنسيات)",
    en: "Mixed (multinational areas)",
    es: "Mixtos (áreas multinacionales)",
  },
  // POI (по ключу)
  "poi.attraction": { ar: "معلم", en: "Attraction", es: "Atracción" },
  "poi.mall": { ar: "مول", en: "Mall", es: "Centro comercial" },
  "poi.park": { ar: "حديقة", en: "Park", es: "Parque" },
  "poi.beach": { ar: "شاطئ", en: "Beach", es: "Playa" },
  "poi.metro": { ar: "مترو", en: "Metro", es: "Metro" },
  // Карточка здания
  "card.price": { ar: "السعر", en: "Price", es: "Precio" },
  "card.rent": { ar: "الإيجار", en: "Rent", es: "Alquiler" },
  "card.service_charge": { ar: "رسوم الخدمة", en: "Service Charge", es: "Cargo de servicio" },
  "card.cooling": { ar: "التبريد (تقديري)", en: "Cooling (est.)", es: "Refrigeración (est.)" },
  "card.cooling_provider": { ar: "مزود التبريد", en: "Cooling provider", es: "Proveedor de refrigeración" },
  "card.true_cost": { ar: "التكلفة الحقيقية للتملك (تقديري)", en: "True cost of ownership (est.)", es: "Costo real de propiedad (est.)" },
  "card.running_costs": { ar: "التكاليف السنوية", en: "Running costs", es: "Costos anuales" },
  "card.built_year": { ar: "سنة البناء", en: "Built Year", es: "Año de construcción" },
  "card.floors": { ar: "الطوابق", en: "Floors", es: "Pisos" },
  "card.units": { ar: "الوحدات", en: "Units", es: "Unidades" },
  "card.parking": { ar: "مواقف السيارات", en: "Parking Ratio", es: "Estacionamiento" },
  "card.no_data": { ar: "لا توجد بيانات", en: "No data", es: "Sin datos" },
  "card.loading": { ar: "جار التحميل…", en: "Loading…", es: "Cargando…" },
  "card.cooling_note": {
    ar: "التبريد تقدير من التعرفات المنشورة، وليس فاتورة",
    en: "Cooling is an estimate from published tariffs, not a bill",
    es: "La refrigeración es una estimación de tarifas publicadas, no una factura",
  },
  "card.geometry": { ar: "الشكل الهندسي", en: "Geometry", es: "Geometría" },
  "card.sales_sample": { ar: "عينة المبيعات", en: "Sales sample", es: "Muestra de ventas" },
  "card.example": { ar: "مثال", en: "Example", es: "Ejemplo" },
  "card.per_year": { ar: "/ سنة", en: "/ yr", es: "/ año" },
  "card.per_month": { ar: "/ شهر", en: "/ mo", es: "/ mes" },
  // Карточка района
  "district.badge": { ar: "تقديري · ليست إحصاءات رسمية", en: "Indicative · not official statistics", es: "Indicativo · no oficial" },
  "district.who_lives": { ar: "من يسكن غالباً", en: "Who mostly lives here", es: "Quién vive principalmente" },
  "district.sources": { ar: "المصادر", en: "Sources", es: "Fuentes" },
  // Кнопки
  "app.about": { ar: "عن البيانات", en: "About data", es: "Sobre los datos" },
  "app.admin": { ar: "المشرف", en: "Admin", es: "Admin" },
  // Модалка выбора языка
  "lang.choose": { ar: "اختر لغتك", en: "Choose your language", es: "Elige tu idioma" },
  "lang.subtitle": {
    ar: "يمكنك تغييرها في أي وقت — الزاوية العلوية اليسرى",
    en: "You can change it anytime — top-left corner",
    es: "Puedes cambiarlo en cualquier momento — arriba a la izquierda",
  },
};

export function tr(key: string, lang: Lang): string {
  return TR[key]?.[lang] ?? key;
}

/** Хук: возвращает функцию перевода t(key). Реагирует на смену языка в store. */
export function useT(): (key: string) => string {
  const lang = useAppStore((s) => s.lang) ?? "en";
  return (key: string) => tr(key, lang);
}
