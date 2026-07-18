// 3D-здания на deck.gl поверх MapLibre.
//
// Зачем не fill-extrusion: MapLibre рисует грани матовой заливкой без текстур —
// нельзя нанести окна, сохранив ценовую раскраску (fill-extrusion-pattern
// заменяет цвет). deck.gl даёт кастомный шейдер: процедурные окна + подсветка
// + глянцевый материал, а цвет здания по-прежнему = цена (heat).
//
// Данные — те же MVT-тайлы /api/tiles/{layer}/{z}/{x}/{y}.pbf (свойства
// value / height_m / id). Слой закодирован в URL; при смене пересобираем слой.

import {
  LayerExtension,
  LightingEffect,
  AmbientLight,
  _SunLight as SunLight,
} from "@deck.gl/core";
import { MVTLayer } from "@deck.gl/geo-layers";
import { LAYERS, NO_DATA_COLOR } from "../../layers.config";

const TILES_VERSION = 4;

type RGB = [number, number, number];

function hexToRgb(hex: string): RGB {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

const NO_DATA_RGB = hexToRgb(NO_DATA_COLOR);

// Приём UrbanCost: для «стоимостных» слоёв высота = ЗНАЧЕНИЕ метрики
// (дороже = выше). k — множитель значения→метры, cap — потолок.
const VALUE_HEIGHT: Record<string, { k: number; cap: number }> = {
  price_sqft: { k: 0.16, cap: 850 },
  rent_sqft: { k: 4.6, cap: 820 },
  service_charge: { k: 22, cap: 720 },
  cooling_est: { k: 34, cap: 640 },
};

function heightForFeature(layerId: string, props: Record<string, unknown>): number {
  const vh = VALUE_HEIGHT[layerId];
  const value = props.value;
  if (vh) {
    if (value == null) return 0;
    return Math.min(vh.cap, Math.max(0, Number(value)) * vh.k);
  }
  // built_year / parking_ratio — по реальной высоте здания
  const h = props.height_m;
  return h == null ? 14 : Number(h);
}

// Плавный градиент цвета по порогам слоя (порт buildColorExpression в JS).
function colorForFeature(layerId: string, props: Record<string, unknown>): [number, number, number, number] {
  const value = props.value;
  if (value == null) return [...NO_DATA_RGB, 255];
  const def = LAYERS.find((l) => l.id === layerId)!;
  const v = Number(value);
  // stops: 0 -> colors[0], thresholds[i] -> colors[i+1]
  const stops: Array<{ at: number; rgb: RGB }> = [{ at: 0, rgb: hexToRgb(def.colors[0]) }];
  def.thresholds.forEach((t, i) => stops.push({ at: t, rgb: hexToRgb(def.colors[i + 1]) }));
  if (v <= stops[0].at) return [...stops[0].rgb, 255];
  const last = stops[stops.length - 1];
  if (v >= last.at) return [...last.rgb, 255];
  for (let i = 1; i < stops.length; i++) {
    if (v <= stops[i].at) {
      const a = stops[i - 1];
      const b = stops[i];
      const t = (v - a.at) / (b.at - a.at || 1);
      return [
        Math.round(a.rgb[0] + (b.rgb[0] - a.rgb[0]) * t),
        Math.round(a.rgb[1] + (b.rgb[1] - a.rgb[1]) * t),
        Math.round(a.rgb[2] + (b.rgb[2] - a.rgb[2]) * t),
        255,
      ];
    }
  }
  return [...last.rgb, 255];
}

// Процедурные окна + подсветка. Инжектим в шейдер SolidPolygonLayer:
//  VS: пробрасываем высоту (м), план-координаты (м) и нормаль как varying.
//  FS: на боковых гранях рисуем сетку окон (тёмные перемычки), часть «горит».
// Цена-цвет сохраняется — окна лишь модулируют его.
class WindowExtension extends LayerExtension {
  getShaders() {
    return {
      inject: {
        "vs:#decl": `
out vec3 vWin_planM;
out float vWin_elevM;
out vec3 vWin_normal;
`,
        "vs:DECKGL_FILTER_COLOR": `
float vWin_cpm = project_size(1.0);          // общих единиц на метр
vWin_elevM = geometry.position.z / vWin_cpm; // высота над землёй, м
vWin_planM = vec3(geometry.position.xy / vWin_cpm, 0.0);
vWin_normal = geometry.normal;
`,
        "fs:#decl": `
in vec3 vWin_planM;
in float vWin_elevM;
in vec3 vWin_normal;
`,
        "fs:DECKGL_FILTER_COLOR": `
// Щадящий для глаз режим: без «горящих» окон и бликов, широкие мягкие простенки,
// низкий контраст — чтобы движущаяся сетка не мерцала (фотосенситивность).
float vWin_side = 1.0 - abs(vWin_normal.z);        // ~1 стена, ~0 крыша
if (vWin_side > 0.35) {
  float floorH = 4.0;                              // метров на этаж
  float winW   = 4.0;                              // метров на окно
  float row = vWin_elevM / floorH;
  // ось вдоль фасада (перпендикулярно нормали в плане)
  float col = (abs(vWin_normal.x) > abs(vWin_normal.y)) ? vWin_planM.y : vWin_planM.x;
  col = col / winW;
  float fr = fract(row);
  float fc = fract(col);
  // широкие мягкие переходы (0.30) → низкая частота, меньше алиасинга/мерцания
  float mx = smoothstep(0.0, 0.30, fc) * smoothstep(0.0, 0.30, 1.0 - fc);
  float my = smoothstep(0.0, 0.30, fr) * smoothstep(0.0, 0.30, 1.0 - fr);
  float pane = mx * my;                            // 1 внутри стекла, 0 на перемычке
  vec3 frame = color.rgb * 0.82;                   // едва темнее — мягкие простенки
  vec3 c = mix(frame, color.rgb, pane);
  color.rgb = mix(color.rgb, c, vWin_side * 0.5);  // общий эффект приглушён вдвое
}
`,
      },
    };
  }
}

const windowExtension = new WindowExtension();

// Мягкое ровное освещение: сильный заполняющий + слабое «солнце», без резких
// перепадов яркости при вращении (щадит фотосенситивных).
export const buildingsLighting = new LightingEffect({
  ambient: new AmbientLight({ color: [255, 255, 255], intensity: 1.35 }),
  sun: new SunLight({
    timestamp: Date.UTC(2024, 6, 1, 13),
    color: [255, 248, 236],
    intensity: 0.45,
    _shadow: false,
  }),
});

// Матовый материал без спекуляра — никаких бегающих бликов при движении карты.
const GLOSS_MATERIAL = {
  ambient: 0.55,
  diffuse: 0.45,
  shininess: 4,
  specularColor: [10, 12, 16] as [number, number, number],
};

export function makeBuildingsLayer(
  layerId: string,
  onPick: (id: number) => void,
): MVTLayer {
  const url = `${window.location.origin}/api/tiles/${layerId}/{z}/{x}/{y}.pbf?v=${TILES_VERSION}`;
  return new MVTLayer({
    id: `buildings-${layerId}`,
    data: url,
    binary: false, // плоский GeoJSON — аксессоры и пикинг читают properties напрямую
    minZoom: 0,
    maxZoom: 20,
    stroked: false,
    filled: true,
    extruded: true,
    pickable: true,
    autoHighlight: false, // без белой вспышки при наведении (фотосенситивность)
    material: GLOSS_MATERIAL,
    extensions: [windowExtension],
    getFillColor: (f: { properties: Record<string, unknown> }) => colorForFeature(layerId, f.properties),
    getElevation: (f: { properties: Record<string, unknown> }) => heightForFeature(layerId, f.properties),
    onClick: (info: { object?: { properties?: Record<string, unknown> } }) => {
      const id = info.object?.properties?.id;
      if (id != null) onPick(Number(id));
    },
  });
}
