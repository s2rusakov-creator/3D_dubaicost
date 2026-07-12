import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { LAYERS, NO_DATA_COLOR } from "../../layers.config";
import {
  COMMUNITY_STYLES,
  DEFAULT_COMMUNITY_COLOR,
  POI_DEFAULT_COLOR,
  POI_STYLES,
} from "../../overlays.config";
import { tr } from "../../i18n";
import { LANDMARKS, type Landmark } from "../../landmarks.config";
import { useAppStore } from "../../store";

// Бесплатная подложка без ключей и лимитов. Если стиль недоступен,
// альтернативы: .../styles/liberty, .../styles/positron
const MAP_STYLE = "https://tiles.openfreemap.org/styles/dark";

const DUBAI_CENTER: [number, number] = [55.25, 25.12];
const SOURCE_ID = "buildings";
const LAYER_3D_ID = "buildings-3d";
const DEMO_SOURCE = "demographics";
const DEMO_FILL = "demographics-fill";
const DEMO_LINE = "demographics-line";
const POI_SOURCE = "pois";
const POI_CIRCLE = "poi-circle";
const POI_LABEL = "poi-label";
// Версия схемы тайлов: тайлы кэшируются браузером (Cache-Control), при смене
// формата (например, фикс строкового value) поднять — обойдёт устаревший кэш.
const TILES_VERSION = 3;

function buildColorExpression(layerId: string): unknown {
  const def = LAYERS.find((l) => l.id === layerId)!;
  const step: unknown[] = ["step", ["get", "value"], def.colors[0]];
  def.thresholds.forEach((t, i) => step.push(t, def.colors[i + 1]));
  return ["case", ["==", ["get", "value"], null], NO_DATA_COLOR, step];
}

function communityColorExpression(): unknown {
  const match: unknown[] = ["match", ["get", "dominant_community"]];
  for (const [key, style] of Object.entries(COMMUNITY_STYLES)) {
    match.push(key, style.color);
  }
  match.push(DEFAULT_COMMUNITY_COLOR);
  return match;
}

function poiColorExpression(): unknown {
  const match: unknown[] = ["match", ["get", "category"]];
  for (const [key, style] of Object.entries(POI_STYLES)) {
    match.push(key, style.color);
  }
  match.push(POI_DEFAULT_COLOR);
  return match;
}

// Круглый фото-пин достопримечательности (как в Яндекс.Картах)
function createLandmarkElement(lm: Landmark): HTMLDivElement {
  const el = document.createElement("div");
  el.title = lm.name;
  el.style.cssText = [
    "width:46px",
    "height:46px",
    "border-radius:50%",
    `background-image:url('${lm.photo}')`,
    "background-size:cover",
    "background-position:center",
    "border:2px solid #ffffff",
    "box-shadow:0 2px 8px rgba(0,0,0,0.55)",
    "cursor:pointer",
  ].join(";");
  return el;
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const activeLayerId = useAppStore((s) => s.activeLayerId);
  const setSelectedBuilding = useAppStore((s) => s.setSelectedBuilding);
  const showDemographics = useAppStore((s) => s.showDemographics);
  const showPois = useAppStore((s) => s.showPois);
  const setSelectedDistrict = useAppStore((s) => s.setSelectedDistrict);

  const layerRef = useRef(activeLayerId);
  layerRef.current = activeLayerId;
  const showPoisRef = useRef(showPois);
  showPoisRef.current = showPois;
  // Кэш POI (по id) — bbox-фетч на каждый moveend иначе затирал бы объекты,
  // выпавшие из вьюпорты, хотя они не изменились. Здания теперь на векторных
  // тайлах (грузятся сами), кэш им не нужен.
  const poiCacheRef = useRef<Map<number, GeoJSON.Feature>>(new Map());
  const demoLoadedRef = useRef(false);
  // Фото-пины достопримечательностей (HTML-маркеры) — создаются раз, тумблятся с POI
  const landmarkMarkersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: DUBAI_CENTER,
      zoom: 10.5,
      pitch: 45,
      bearing: -20,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");

    const fetchPois = async () => {
      // POI мало (~245) — грузим на любом зуме, чтобы были кликабельны и на обзоре
      if (!showPoisRef.current) return;
      const b = map.getBounds();
      const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
      try {
        const resp = await fetch(`/api/pois?bbox=${bbox}`);
        if (!resp.ok) return;
        const geojson = await resp.json();
        const cache = poiCacheRef.current;
        for (const feature of geojson.features as GeoJSON.Feature[]) {
          const id = feature.properties?.id;
          if (id != null) cache.set(id, feature);
        }
        (map.getSource(POI_SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData({
          type: "FeatureCollection",
          features: Array.from(cache.values()),
        });
      } catch {
        // молча — POI необязательны
      }
    };

    map.on("load", () => {
      // Порядок z: демография (по земле) < здания (3D) < POI-маркеры (сверху)
      map.addSource(DEMO_SOURCE, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: DEMO_FILL,
        type: "fill",
        source: DEMO_SOURCE,
        layout: { visibility: "none" },
        paint: {
          "fill-color": communityColorExpression() as never,
          "fill-opacity": 0.35,
        },
      });
      map.addLayer({
        id: DEMO_LINE,
        type: "line",
        source: DEMO_SOURCE,
        layout: { visibility: "none" },
        paint: { "line-color": "#c8ccd4", "line-width": 1, "line-opacity": 0.5 },
      });

      // Векторные тайлы (MVT) — MapLibre сам подгружает видимую область на любом
      // зуме, без лимита фич и без ручной дозагрузки. Слой в пути URL = цвет тайла.
      map.addSource(SOURCE_ID, {
        type: "vector",
        tiles: [`${window.location.origin}/api/tiles/${layerRef.current}/{z}/{x}/{y}.pbf?v=${TILES_VERSION}`],
        minzoom: 0,
        // Бэкенд генерит тайл на любом зуме — держим высокий maxzoom, иначе выше
        // него MapLibre «оверзумит» грубый тайл, а fill-extrusion на оверзуме
        // не рисуется → здания пропадают на приближении
        maxzoom: 20,
      });
      map.addLayer({
        id: LAYER_3D_ID,
        type: "fill-extrusion",
        source: SOURCE_ID,
        "source-layer": "buildings",
        paint: {
          "fill-extrusion-color": buildColorExpression(layerRef.current) as never,
          "fill-extrusion-height": ["coalesce", ["get", "height_m"], 20],
          "fill-extrusion-opacity": 0.85,
        },
      });

      map.addSource(POI_SOURCE, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: POI_CIRCLE,
        type: "circle",
        source: POI_SOURCE,
        layout: { visibility: "none" },
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 4, 13, 6, 16, 9],
          "circle-color": poiColorExpression() as never,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#12151b",
          "circle-opacity": 0.95,
        },
      });
      map.addLayer({
        id: POI_LABEL,
        type: "symbol",
        source: POI_SOURCE,
        minzoom: 13,
        layout: {
          visibility: "none",
          "text-field": ["get", "name"],
          "text-size": 11,
          "text-offset": [0, 1.1],
          "text-anchor": "top",
          "text-optional": true,
        },
        paint: {
          "text-color": "#e6e9ef",
          "text-halo-color": "#12151b",
          "text-halo-width": 1.4,
        },
      });

      // Фото-пины достопримечательностей — создаём один раз, показываем с оверлеем POI.
      // Клик по пину открывает попап (фото + название) через встроенный setPopup —
      // это надёжнее ручного addEventListener (сам тоглит попап).
      landmarkMarkersRef.current = LANDMARKS.map((lm) => {
        const el = createLandmarkElement(lm);
        const popup = new maplibregl.Popup({ offset: 28, closeButton: true, maxWidth: "220px" }).setHTML(
          `<div style="text-align:center">
             <img src="${lm.photo}" alt="" style="width:190px;height:115px;object-fit:cover;border-radius:8px;display:block" />
             <strong style="display:block;margin-top:6px;font-size:13px">${lm.name}</strong>
           </div>`,
        );
        return new maplibregl.Marker({ element: el }).setLngLat([lm.lng, lm.lat]).setPopup(popup);
      });
      if (showPoisRef.current) {
        landmarkMarkersRef.current.forEach((m) => m.addTo(map));
      }
    });

    map.on("moveend", () => {
      void fetchPois();
    });

    map.on("click", LAYER_3D_ID, (e) => {
      const id = e.features?.[0]?.properties?.id;
      if (id != null) setSelectedBuilding(Number(id));
    });
    map.on("mouseenter", LAYER_3D_ID, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", LAYER_3D_ID, () => (map.getCanvas().style.cursor = ""));

    // Клик по демо-зоне — открыть панель с ориентировочными данными
    map.on("click", DEMO_FILL, (e) => {
      const p = e.features?.[0]?.properties;
      if (!p) return;
      setSelectedDistrict({
        name: String(p.name ?? ""),
        dominant_community: (p.dominant_community as string) ?? null,
        communities: (p.communities as string) ?? null,
        note: (p.note as string) ?? null,
        sources: (p.sources as string) ?? null,
        is_indicative: p.is_indicative === true || p.is_indicative === "true",
      });
    });

    // Попап с названием POI
    const poiPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: true, offset: 12 });
    map.on("click", POI_CIRCLE, (e) => {
      const f = e.features?.[0];
      if (!f || f.geometry.type !== "Point") return;
      const name = f.properties?.name ?? "";
      const cat = String(f.properties?.category ?? "");
      const lang = useAppStore.getState().lang ?? "en";
      const catLabel = tr(`poi.${cat}`, lang) || POI_STYLES[cat]?.label || cat;
      poiPopup
        .setLngLat(f.geometry.coordinates as [number, number])
        .setHTML(`<strong>${name}</strong><br/><span style="opacity:.7">${catLabel}</span>`)
        .addTo(map);
    });
    map.on("mouseenter", POI_CIRCLE, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", POI_CIRCLE, () => (map.getCanvas().style.cursor = ""));

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [setSelectedBuilding, setSelectedDistrict]);

  // Смена слоя: перекрасить и перезапросить данные без перезагрузки карты
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(LAYER_3D_ID)) return;
    // Слой закодирован в URL тайла (значение/цвет) — меняем tiles и перекрашиваем
    const src = map.getSource(SOURCE_ID) as maplibregl.VectorTileSource | undefined;
    src?.setTiles([`${window.location.origin}/api/tiles/${activeLayerId}/{z}/{x}/{y}.pbf?v=${TILES_VERSION}`]);
    map.setPaintProperty(
      LAYER_3D_ID,
      "fill-extrusion-color",
      buildColorExpression(activeLayerId) as never
    );
  }, [activeLayerId]);

  // Демография: ленивая загрузка один раз + переключение видимости
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(DEMO_FILL)) return;
    const vis = showDemographics ? "visible" : "none";
    map.setLayoutProperty(DEMO_FILL, "visibility", vis);
    map.setLayoutProperty(DEMO_LINE, "visibility", vis);
    if (showDemographics && !demoLoadedRef.current) {
      demoLoadedRef.current = true;
      fetch("/api/districts")
        .then((r) => (r.ok ? r.json() : null))
        .then((geojson) => {
          if (geojson) {
            (map.getSource(DEMO_SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData(geojson);
          }
        })
        .catch(() => {
          demoLoadedRef.current = false;
        });
    }
  }, [showDemographics]);

  // POI: переключение видимости + подгрузка для текущего вида
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(POI_CIRCLE)) return;
    const vis = showPois ? "visible" : "none";
    map.setLayoutProperty(POI_CIRCLE, "visibility", vis);
    map.setLayoutProperty(POI_LABEL, "visibility", vis);
    // Фото-пины достопримечательностей — добавляем/убираем вместе с оверлеем
    if (showPois) {
      landmarkMarkersRef.current.forEach((m) => m.addTo(map));
      map.fire("moveend");
    } else {
      landmarkMarkersRef.current.forEach((m) => m.remove());
    }
  }, [showPois]);

  return <div ref={containerRef} className="map-container" />;
}
