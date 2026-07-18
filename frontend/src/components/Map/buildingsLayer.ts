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
// Uniform-модуль: общая позиция фиксированной мировой точки (центр Дубая) в
// координатах текущего кадра — считается в draw() и кладётся через setShaderModuleProps.
const winShaderModule = {
  name: "win",
  vs: `
layout(std140) uniform winUniforms {
  vec2 refCommon;
} win;
`,
  uniformTypes: { refCommon: "vec2<f32>" },
};

class WindowExtension extends LayerExtension {
  getShaders() {
    return {
      modules: [winShaderModule],
      inject: {
        "vs:#decl": `
out vec2 vWin_planM;
out float vWin_elevM;
out vec3 vWin_normal;
`,
        "vs:DECKGL_FILTER_COLOR": `
// Координаты относительно фиксированной точки (центр Дубая): и geometry.position,
// и win.refCommon несут один и тот же по-кадровый сдвиг deck (commonOrigin) →
// их разность от камеры НЕ зависит → сетка окон статична при панораме/вращении.
// Числа малы (в пределах города) → высокая точность float.
float vWin_mpc = 1.0 / project_size(1.0);
vWin_planM = (geometry.position.xy - win.refCommon) * vWin_mpc;
vWin_elevM = geometry.position.z * vWin_mpc;
vWin_normal = geometry.normal;
`,
        "fs:#decl": `
in vec2 vWin_planM;
in float vWin_elevM;
in vec3 vWin_normal;
float vWin_hash(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
// Антиалиасинговая линия сетки: 1 внутри ячейки (стекло), 0 на линии (простенок).
// Ширина линии = экранный размер (fwidth) → вблизи чётко, а не рвано.
float vWin_axis(float x, float lh){
  float d = abs(fract(x) - 0.5);
  float w = fwidth(x) + 1e-5;
  return 1.0 - smoothstep(0.5 - lh - w, 0.5 - lh + w, d);
}
`,
        "fs:DECKGL_FILTER_COLOR": `
// Высота здания закодирована в альфе fill-цвета (см. getFillColor). Читаем и сразу
// возвращаем альфу=1, чтобы здание оставалось непрозрачным.
float vWin_topM = color.a * 1000.0;
color.a = 1.0;
float vWin_side = 1.0 - abs(vWin_normal.z);        // ~1 стена, ~0 крыша
if (vWin_side > 0.35) {
  float floorH = 3.6;                              // метров на этаж
  float winW   = 3.6;                              // метров на окно
  float row = vWin_elevM / floorH;
  // ось вдоль фасада (перпендикулярно нормали в плане)
  float col = (abs(vWin_normal.x) > abs(vWin_normal.y)) ? vWin_planM.y : vWin_planM.x;
  col = col / winW;
  // видимость гаснет, когда ячейка мельче ~1.5px → плоский цвет (без шума вдали)
  float vis = 1.0 - smoothstep(0.3, 0.6, max(fwidth(col), fwidth(row)));
  float pane = vWin_axis(col, 0.14) * vWin_axis(row, 0.14);
  vec3 frame = color.rgb * 0.45;                   // тёмные простенки (видимые)
  vec3 c = mix(frame, color.rgb, pane);
  // горящие окна (детерминированный шум по ячейке)
  float lit = step(0.65, vWin_hash(floor(vec2(col, row))));
  c += lit * pane * vec3(1.0, 0.85, 0.55) * 0.5;
  color.rgb = mix(color.rgb, c, vWin_side * vis); // vis: всё гаснет вдали, без ряби
  // Белый кант по верхней кромке стены (у крыши). Гаснет вместе с окнами (vis),
  // поэтому на дальнем зуме контура нет — рисуется с той же дистанции, что окна.
  float edge = smoothstep(vWin_topM - 2.0, vWin_topM - 0.4, vWin_elevM);
  // на низких зданиях кант не нужен: под ~18 м его нет, к ~45 м — на полную
  float hgate = smoothstep(18.0, 45.0, vWin_topM);
  color.rgb = mix(color.rgb, vec3(1.0), edge * vis * hgate * 0.9);
} else {
  // КРЫШИ: чистая тёмная матовая «шапка».
  color.rgb *= 0.66;
}
`,
      },
    };
  }

  draw() {
    // Фикс-точка = начало тайла: projectPosition (метод слоя) даёт её в ТОЙ ЖЕ
    // сдвинутой системе, что и шейдерный geometry.position, поэтому в разности
    // по-кадровый сдвиг сокращается, а число мало́ (в пределах тайла) → точно.
    const self = this as unknown as {
      projectPosition: (p: number[]) => number[];
      setShaderModuleProps: (props: Record<string, unknown>) => void;
    };
    const r = self.projectPosition([0, 0, 0]);
    self.setShaderModuleProps({ win: { refCommon: [r[0], r[1]] } });
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
    // Альфу fill-цвета используем как переносчик высоты здания (0..1000 м → 0..255):
    // шейдер читает её для белого канта, затем ставит альфу=1 (непрозрачно).
    getFillColor: (f: { properties: Record<string, unknown> }) => {
      const [r, g, b] = colorForFeature(layerId, f.properties);
      const h = Math.max(0, Math.min(1000, heightForFeature(layerId, f.properties)));
      // округляем ВНИЗ: декодированная вершина ≤ реальной → кант всегда дотянется до крыши
      return [r, g, b, Math.floor((h / 1000) * 255)];
    },
    getElevation: (f: { properties: Record<string, unknown> }) => heightForFeature(layerId, f.properties),
    onClick: (info: { object?: { properties?: Record<string, unknown> } }) => {
      const id = info.object?.properties?.id;
      if (id != null) onPick(Number(id));
    },
  });
}
