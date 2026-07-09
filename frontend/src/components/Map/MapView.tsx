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
import { useAppStore } from "../../store";

// Бесплатная подложка без ключей и лимитов. Если стиль недоступен,
// альтернативы: .../styles/liberty, .../styles/positron
const MAP_STYLE = "https://tiles.openfreemap.org/styles/dark";

const DUBAI_CENTER: [number, number] = [55.2744, 25.1972];
const SOURCE_ID = "buildings";
const LAYER_3D_ID = "buildings-3d";
const DEMO_SOURCE = "demographics";
const DEMO_FILL = "demographics-fill";
const DEMO_LINE = "demographics-line";
const POI_SOURCE = "pois";
const POI_CIRCLE = "poi-circle";
const POI_LABEL = "poi-label";
const MIN_FETCH_ZOOM = 13;

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
  // Кэш уже полученных зданий/POI (по id) — bbox-фетч на каждый moveend иначе
  // затирал бы объекты, выпавшие из текущей вьюпорты, хотя они не изменились
  const featuresCacheRef = useRef<Map<number, GeoJSON.Feature>>(new Map());
  const poiCacheRef = useRef<Map<number, GeoJSON.Feature>>(new Map());
  const demoLoadedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: DUBAI_CENTER,
      zoom: 14,
      pitch: 55,
      bearing: -20,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");

    const fetchBuildings = async () => {
      if (map.getZoom() < MIN_FETCH_ZOOM) return;
      const b = map.getBounds();
      const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
      try {
        const resp = await fetch(`/api/map?bbox=${bbox}&layer=${layerRef.current}`);
        if (!resp.ok) return;
        const geojson = await resp.json();
        const cache = featuresCacheRef.current;
        for (const feature of geojson.features as GeoJSON.Feature[]) {
          const id = feature.properties?.id;
          if (id != null) cache.set(id, feature);
        }
        (map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined)?.setData({
          type: "FeatureCollection",
          features: Array.from(cache.values()),
        });
      } catch {
        // API недоступен (dev без бэкенда) — карта остаётся пустой
      }
    };

    const fetchPois = async () => {
      if (!showPoisRef.current || map.getZoom() < MIN_FETCH_ZOOM) return;
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

      map.addSource(SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        // По умолчанию GeoJSON-источник упрощает геометрию на дальних зумах
        // (tolerance 0.375) — мелкие полигоны зданий схлопываются и исчезают
        tolerance: 0,
      });
      map.addLayer({
        id: LAYER_3D_ID,
        type: "fill-extrusion",
        source: SOURCE_ID,
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
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 5, 16, 9],
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
        minzoom: 14,
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

      fetchBuildings();
    });

    map.on("moveend", () => {
      void fetchBuildings();
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
      const catLabel = POI_STYLES[cat]?.label ?? cat;
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
    // value в кэше специфичен для слоя — при смене слоя кэш неактуален
    featuresCacheRef.current.clear();
    map.setPaintProperty(
      LAYER_3D_ID,
      "fill-extrusion-color",
      buildColorExpression(activeLayerId) as never
    );
    map.fire("moveend"); // триггерит fetchBuildings с новым слоем
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
    if (showPois) map.fire("moveend");
  }, [showPois]);

  return <div ref={containerRef} className="map-container" />;
}
