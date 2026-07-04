import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { LAYERS, NO_DATA_COLOR } from "../../layers.config";
import { useAppStore } from "../../store";

// Бесплатная подложка без ключей и лимитов. Если стиль недоступен,
// альтернативы: .../styles/liberty, .../styles/positron
const MAP_STYLE = "https://tiles.openfreemap.org/styles/dark";

const DUBAI_CENTER: [number, number] = [55.2744, 25.1972];
const SOURCE_ID = "buildings";
const LAYER_3D_ID = "buildings-3d";
const MIN_FETCH_ZOOM = 13;

function buildColorExpression(layerId: string): unknown {
  const def = LAYERS.find((l) => l.id === layerId)!;
  const step: unknown[] = ["step", ["get", "value"], def.colors[0]];
  def.thresholds.forEach((t, i) => step.push(t, def.colors[i + 1]));
  return ["case", ["==", ["get", "value"], null], NO_DATA_COLOR, step];
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const activeLayerId = useAppStore((s) => s.activeLayerId);
  const setSelectedBuilding = useAppStore((s) => s.setSelectedBuilding);
  const layerRef = useRef(activeLayerId);
  layerRef.current = activeLayerId;

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
        (map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined)?.setData(geojson);
      } catch {
        // API недоступен (dev без бэкенда) — карта остаётся пустой
      }
    };

    map.on("load", () => {
      map.addSource(SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
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
      fetchBuildings();
    });

    map.on("moveend", fetchBuildings);

    map.on("click", LAYER_3D_ID, (e) => {
      const id = e.features?.[0]?.properties?.id;
      if (id != null) setSelectedBuilding(Number(id));
    });
    map.on("mouseenter", LAYER_3D_ID, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", LAYER_3D_ID, () => (map.getCanvas().style.cursor = ""));

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [setSelectedBuilding]);

  // Смена слоя: перекрасить и перезапросить данные без перезагрузки карты
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(LAYER_3D_ID)) return;
    map.setPaintProperty(
      LAYER_3D_ID,
      "fill-extrusion-color",
      buildColorExpression(activeLayerId) as never
    );
    map.fire("moveend"); // триггерит fetchBuildings с новым слоем
  }, [activeLayerId]);

  return <div ref={containerRef} className="map-container" />;
}
