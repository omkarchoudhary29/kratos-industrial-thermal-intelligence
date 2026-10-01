import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Region, ThermalEvent, ThermalSource, OSMFacilityFeature } from '../types';
import { api } from '../services/api';
import { useSelectedFeature, BasemapId } from '../context/SelectedFeatureContext';
import {
  Layers,
  MapPin,
  Maximize2,
  Crosshair,
  Bot,
  Flame,
  Factory,
  Zap,
  Activity,
  Trees,
  Compass,
} from 'lucide-react';

interface IndiaMapProps {
  regions: Region[];
  selectedRegion: Region | null;
  events: ThermalEvent[];
  sources?: ThermalSource[];
  onSelectEvent?: (event: ThermalEvent) => void;
  onSelectRegion?: (region: Region) => void;
  onGenerateReport?: (scope: 'region' | 'viewport' | 'feature', featureType?: string, featureId?: string) => void;
  onCreateFollowUp?: (featureType: string, featureId: string, name: string, region: string) => void;
  cartoApiKey?: string | null;
}

const BASEMAP_ZOOM_CONFIG: Record<BasemapId, { maxNativeZoom: number; maxZoom: number; label: string }> = {
  satellite: { maxNativeZoom: 18, maxZoom: 20, label: 'Esri World Imagery' },
  hybrid: { maxNativeZoom: 18, maxZoom: 20, label: 'Esri World Imagery Hybrid' },
  street: { maxNativeZoom: 19, maxZoom: 20, label: 'OpenStreetMap Standard' },
  dark: { maxNativeZoom: 16, maxZoom: 20, label: 'Esri Dark Canvas' },
  light: { maxNativeZoom: 16, maxZoom: 20, label: 'Esri Light Canvas' },
  terrain: { maxNativeZoom: 18, maxZoom: 20, label: 'Esri World Topo Map' },
};

export const IndiaMap: React.FC<IndiaMapProps> = ({
  regions,
  selectedRegion,
  events,
  sources = [],
  onSelectEvent,
  onSelectRegion,
  onGenerateReport,
  onCreateFollowUp,
  cartoApiKey,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const [currentZoom, setCurrentZoom] = useState(5);
  const baseLayersRef = useRef<Record<BasemapId, L.Layer | null>>({
    satellite: null,
    hybrid: null,
    street: null,
    dark: null,
    light: null,
    terrain: null,
  });

  const {
    selectedFeature,
    setSelectedFeature,
    askAIAboutFeature,
    activeBasemap,
    setActiveBasemap,
  } = useSelectedFeature();

  // Layer groups
  const facilitiesLayerRef = useRef<L.LayerGroup | null>(null);
  const regionsLayerRef = useRef<L.LayerGroup | null>(null);
  const observationsLayerRef = useRef<L.LayerGroup | null>(null);
  const clustersLayerRef = useRef<L.LayerGroup | null>(null);

  // Layer toggle states
  const [showClusters, setShowClusters] = useState(true);
  const [showObservations, setShowObservations] = useState(true);
  const [showIndustrial, setShowIndustrial] = useState(true);
  const [showPower, setShowPower] = useState(true);
  const [showRefinery, setShowRefinery] = useState(true);
  const [showMining, setShowMining] = useState(true);
  const [showRegions, setShowRegions] = useState(true);

  // UI state
  const [isLayerPanelOpen, setIsLayerPanelOpen] = useState(false);
  const [facilities, setFacilities] = useState<OSMFacilityFeature[]>([]);
  const [facilityCounts, setFacilityCounts] = useState<Record<string, number>>({});
  const [isLoadingFacilities, setIsLoadingFacilities] = useState(false);

  // Global window functions to bridge Leaflet popup HTML actions to React
  useEffect(() => {
    (window as any).__kratos_ask_ai__ = (type: string, id: string, name: string, lat: number, lon: number, extraJson?: string) => {
      let props: any = {};
      try {
        if (extraJson) props = JSON.parse(decodeURIComponent(extraJson));
      } catch (e) {}

      askAIAboutFeature({
        type: type as any,
        id,
        name,
        latitude: lat,
        longitude: lon,
        regionName: props.region_name || props.region,
        properties: props,
        association: props.nearest_facility ? {
          nearestFacilityName: props.nearest_facility.name,
          nearestCategory: props.nearest_facility.category,
          distanceM: props.nearest_facility.distance_metres || props.distance_to_nearest_industry_m,
          relationship: props.nearest_facility.relationship_tier,
        } : undefined,
      });
    };

    (window as any).__kratos_zoom_to__ = (lat: number, lon: number, zoom = 14) => {
      mapInstanceRef.current?.flyTo([lat, lon], zoom, { duration: 1.2 });
    };

    (window as any).__kratos_generate_report__ = (scope: string, featType: string, featId: string, region: string) => {
      if (onGenerateReport) {
        onGenerateReport(scope as any, featType, featId);
      }
    };

    (window as any).__kratos_create_followup__ = (featType: string, featId: string, name: string, region: string) => {
      if (onCreateFollowUp) {
        onCreateFollowUp(featType, featId, name, region);
      }
    };

    return () => {
      delete (window as any).__kratos_ask_ai__;
      delete (window as any).__kratos_zoom_to__;
      delete (window as any).__kratos_generate_report__;
      delete (window as any).__kratos_create_followup__;
    };
  }, [askAIAboutFeature, onGenerateReport, onCreateFollowUp]);

  // 1. Initialize Map and Basemaps
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [21.5, 80.0],
      zoom: 5,
      minZoom: 4,
      maxZoom: 20,
      zoomControl: false,
      attributionControl: true,
    });

    map.on('zoomend', () => {
      setCurrentZoom(map.getZoom());
    });

    // Custom zoom control in bottom-left
    L.control.zoom({ position: 'bottomleft' }).addTo(map);

    // Setup 6 Verified Basemap Providers with Provider-Specific Native Zoom Limits
    // A. Satellite / World Imagery (Esri) - native 18, scaled to 20
    const satelliteLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        maxNativeZoom: 18,
        maxZoom: 20,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      }
    );

    // B. Hybrid (Satellite + Boundaries & Places) - native 18, scaled to 20
    const hybridBase = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxNativeZoom: 18, maxZoom: 20 }
    );
    const hybridRef = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      { maxNativeZoom: 18, maxZoom: 20, attribution: '&copy; Esri, Maxar, Earthstar Geographics &mdash; Boundaries & Places' }
    );
    const hybridLayer = L.layerGroup([hybridBase, hybridRef]);

    // C. Street Map (OpenStreetMap Standard) - native 19, scaled to 20
    const streetLayer = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxNativeZoom: 19,
        maxZoom: 20,
        subdomains: ['a', 'b', 'c'],
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }
    );

    // D. Dark Map (Esri Dark Canvas or CARTO Dark) - native 16, scaled to 20
    const activeCartoKey =
      cartoApiKey ||
      (import.meta as any).env?.VITE_CARTO_API_KEY ||
      (window as any).__CARTO_API_KEY__;

    let darkLayer: L.Layer;
    if (activeCartoKey) {
      darkLayer = L.tileLayer(
        `https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png?key=${encodeURIComponent(
          activeCartoKey
        )}`,
        {
          maxNativeZoom: 19,
          maxZoom: 20,
          subdomains: 'abcd',
          attribution: '&copy; <a href="https://carto.com/">CARTO</a> contributors',
        }
      );
    } else {
      const darkBase = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        { maxNativeZoom: 16, maxZoom: 20 }
      );
      const darkRef = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
        { maxNativeZoom: 16, maxZoom: 20, attribution: '&copy; Esri, DeLorme, NAVTEQ' }
      );
      darkLayer = L.layerGroup([darkBase, darkRef]);
    }

    // E. Light Map (Esri Light Gray Canvas) - native 16, scaled to 20
    const lightBase = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      { maxNativeZoom: 16, maxZoom: 20 }
    );
    const lightRef = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      { maxNativeZoom: 16, maxZoom: 20, attribution: '&copy; Esri, DeLorme, NAVTEQ' }
    );
    const lightLayer = L.layerGroup([lightBase, lightRef]);

    // F. Terrain / Topographic (Esri World Topo Map) - native 18, scaled to 20
    const terrainLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
      {
        maxNativeZoom: 18,
        maxZoom: 20,
        attribution: '&copy; Esri &mdash; DeLorme, NAVTEQ, TomTom',
      }
    );

    baseLayersRef.current = {
      satellite: satelliteLayer,
      hybrid: hybridLayer,
      street: streetLayer,
      dark: darkLayer,
      light: lightLayer,
      terrain: terrainLayer,
    };

    // Add default basemap
    satelliteLayer.addTo(map);

    // Dedicated Z-Index Panes to guarantee marker clickability across basemaps and overlays
    if (!map.getPane('facilitiesPane')) {
      const p = map.createPane('facilitiesPane');
      p.style.zIndex = '450';
    }
    if (!map.getPane('observationsPane')) {
      const p = map.createPane('observationsPane');
      p.style.zIndex = '620';
    }
    if (!map.getPane('clustersPane')) {
      const p = map.createPane('clustersPane');
      p.style.zIndex = '650';
    }

    // Initialize overlay groups in strict bottom-to-top z-order
    facilitiesLayerRef.current = L.layerGroup().addTo(map);
    regionsLayerRef.current = L.layerGroup().addTo(map);
    clustersLayerRef.current = L.layerGroup().addTo(map);
    observationsLayerRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [cartoApiKey]);

  // 2. Switch Basemap (Preserves center, zoom, and overlays)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const layers = baseLayersRef.current;
    // Remove all base layers
    Object.values(layers).forEach((layer) => {
      if (layer && map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });

    // Add new selected base layer
    const targetLayer = layers[activeBasemap];
    if (targetLayer) {
      targetLayer.addTo(map);
      // Bring base layer to back so overlays stay visible
      if ((targetLayer as any).bringToBack) {
        (targetLayer as any).bringToBack();
      }
    }
  }, [activeBasemap]);

  // 3. Fetch OSM Facilities when selectedRegion changes
  useEffect(() => {
    let isCancelled = false;
    setIsLoadingFacilities(true);

    const regionId = selectedRegion?.event_id || (selectedRegion as any)?.id;
    const params: { region_id?: number; limit?: number } = { limit: 500 };
    if (regionId && typeof regionId === 'number') {
      params.region_id = regionId;
    }

    api
      .getOsmFacilities(params)
      .then((res) => {
        if (isCancelled) return;
        const feats = res.features || [];
        setFacilities(feats);

        const counts: Record<string, number> = {};
        feats.forEach((f) => {
          const cat = f.properties.facility_category || 'other';
          counts[cat] = (counts[cat] || 0) + 1;
        });
        setFacilityCounts(counts);
        setIsLoadingFacilities(false);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.warn('Failed loading OSM facilities:', err);
        setFacilities([]);
        setFacilityCounts({});
        setIsLoadingFacilities(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedRegion]);

  // 4. Render Persistent Thermal Clusters Layer (DBSCAN 300m Sources)
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = clustersLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    if (!showClusters) return;

    const displaySources = selectedRegion
      ? sources.filter((s) => (s.region_name || '').toLowerCase() === (selectedRegion.id || '').toLowerCase() || s.region_name === selectedRegion.name)
      : sources;

    displaySources.forEach((src) => {
      const lat = src.latitude;
      const lon = src.longitude;
      if (!lat || !lon) return;

      const sourceId = src.thermal_source_id || 'source';
      const isClassified = Boolean(src.source_class && src.source_class !== 'unknown' && src.source_class !== 'unclassified');
      const classLabel = isClassified && src.source_class
        ? src.source_class.replace(/_/g, ' ').toUpperCase()
        : 'UNCLASSIFIED';
      const confStr = src.classification_confidence !== null && src.classification_confidence !== undefined
        ? `${Math.round(src.classification_confidence * 100)}% (Heuristic)`
        : 'Uncalibrated / Unavailable';

      const hits = src.detection_count ?? (src as any).total_detections ?? 0;
      const meanFrp = src.mean_frp ? src.mean_frp.toFixed(1) : 'N/A';
      const maxFrp = src.max_frp ? src.max_frp.toFixed(1) : 'N/A';
      const persistenceVal = (src as any).persistence_30d_mean ?? src.persistence_ratio;
      const persistence = persistenceVal !== undefined && persistenceVal !== null
        ? `${(persistenceVal * 100).toFixed(1)}%`
        : 'N/A';

      // Render as distinct Glowing Diamond Marker
      const diamondIcon = L.divIcon({
        className: 'custom-cluster-marker',
        html: `
          <div style="position: relative; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;">
            <div style="position: absolute; width: 14px; height: 14px; transform: rotate(45deg); background-color: #F59E0B; border: 2px solid #FFFFFF; box-shadow: 0 0 10px rgba(245, 158, 11, 0.85); border-radius: 2px;"></div>
            <div style="position: absolute; width: 6px; height: 6px; background-color: #070A10; border-radius: 50%;"></div>
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const marker = L.marker([lat, lon], {
        icon: diamondIcon,
        pane: 'clustersPane',
        bubblingMouseEvents: false,
      });

      const safeExtra = encodeURIComponent(JSON.stringify(src));

      // Reference Image 3 Styled Target Popup
      const popupHtml = `
        <div style="font-family: Inter, sans-serif; font-size: 11px; width: 280px; background: #0D131F; color: #E2E8F0; border-radius: 8px; overflow: hidden; border: 1px solid #2A374D;">
          <!-- Top Badge Header -->
          <div style="padding: 10px 12px 8px; background: #070A10; border-bottom: 1px solid #1E293B;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 9px; font-weight: 800; font-family: monospace; letter-spacing: 0.05em; color: #F59E0B; background: rgba(245, 158, 11, 0.15); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.3);">
                PERSISTENT CLUSTER
              </span>
              <span style="font-size: 9px; font-weight: 700; color: #10B981; background: rgba(16, 185, 129, 0.15); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3);">
                RECURRING
              </span>
            </div>
            <div style="font-size: 13px; font-weight: 700; color: #FFFFFF; font-family: monospace; margin-top: 2px;">
              ${sourceId}
            </div>
            <div style="font-size: 10px; color: #94A3B8; font-family: monospace; margin-top: 2px;">
              ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E · ${src.region_name || 'Corridor'}
            </div>
          </div>

          <!-- Body Content -->
          <div style="padding: 10px 12px; display: flex; flex-direction: column; gap: 8px;">
            <!-- Assessment Section -->
            <div style="background: #121927; padding: 8px; border-radius: 6px; border: 1px solid #1E293B;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                <span style="color: #94A3B8; font-size: 10px;">Classification:</span>
                <span style="font-weight: 700; color: ${isClassified ? '#F59E0B' : '#94A3B8'}; font-family: monospace;">${classLabel}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #94A3B8; font-size: 10px;">Heuristic Rating:</span>
                <span style="font-size: 10px; color: #E2E8F0; font-family: monospace;">${confStr}</span>
              </div>
            </div>

            <!-- Thermal History Grid -->
            <div style="display: grid; grid-cols: 2; gap: 6px; background: #121927; padding: 8px; border-radius: 6px; border: 1px solid #1E293B;">
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94A3B8;">Total Observations:</span>
                <span style="font-weight: 700; color: #FFFFFF; font-family: monospace;">${hits} hits</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94A3B8;">30-Day Persistence:</span>
                <span style="font-weight: 600; color: #F59E0B; font-family: monospace;">${persistence}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94A3B8;">Mean / Peak FRP:</span>
                <span style="font-family: monospace; color: #E2E8F0;">${meanFrp} / ${maxFrp} MW</span>
              </div>
            </div>

            <!-- Scientific Safeguard Notice -->
            <div style="font-size: 9px; color: #64748B; line-height: 1.35; padding: 4px 6px; background: #0A0E17; border-left: 2px solid #F59E0B; border-radius: 0 4px 4px 0;">
              Clustered via EPSG:7755 DBSCAN (300m). Unclassified sources require on-site validation.
            </div>

            <!-- Action Buttons -->
            <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 4px;">
              <div style="display: flex; gap: 4px;">
                <button
                  onclick="window.__kratos_ask_ai__('cluster', '${sourceId}', '${sourceId}', ${lat}, ${lon}, '${safeExtra}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 5px 8px; background: #F59E0B; color: #070A10; font-weight: 700; font-size: 10px; border-radius: 4px; border: none; cursor: pointer;"
                >
                  <span>Ask AI Investigator</span>
                </button>
                <button
                  onclick="window.__kratos_zoom_to__(${lat}, ${lon}, 16)"
                  style="padding: 5px 8px; background: #1E293B; color: #E2E8F0; font-size: 10px; font-weight: 600; border-radius: 4px; border: 1px solid #334155; cursor: pointer;"
                >
                  Zoom
                </button>
              </div>
              <div style="display: flex; gap: 4px;">
                <button
                  onclick="window.__kratos_generate_report__('feature', 'cluster', '${sourceId}', '${src.region_name || 'Corridor'}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 3px; padding: 5px 8px; background: #0F172A; color: #38BDF8; font-weight: 600; font-size: 9.5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.4); cursor: pointer;"
                >
                  <span>Investigation Report</span>
                </button>
                <button
                  onclick="window.__kratos_create_followup__('cluster', '${sourceId}', 'Cluster ${sourceId}', '${src.region_name || 'Corridor'}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 3px; padding: 5px 8px; background: #0F172A; color: #F59E0B; font-weight: 600; font-size: 9.5px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.4); cursor: pointer;"
                >
                  <span>Create Follow-up</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { maxWidth: 320, className: 'kratos-custom-popup' });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        setSelectedFeature({
          type: 'cluster',
          id: sourceId,
          name: `Cluster ${sourceId}`,
          latitude: lat,
          longitude: lon,
          regionName: src.region_name,
          properties: src,
        });
      });

      marker.addTo(layer);
    });
  }, [sources, selectedRegion, showClusters, setSelectedFeature]);

  // 5. Render Thermal Observations / Events Layer with Anti-Collision Jitter and High-Z Panes
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = observationsLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    if (!showObservations) return;

    const coordCounts: Record<string, number> = {};

    events.forEach((ev) => {
      const risk = ev.final_risk_level;
      let color = '#10B981'; // normal / low (green)
      let radius = 7;

      if (risk === 'critical') {
        color = '#EF4444'; // critical (red)
        radius = 9;
      } else if (risk === 'high') {
        color = '#F97316'; // high (orange)
        radius = 8;
      } else if (risk === 'medium') {
        color = '#EAB308'; // medium (yellow)
        radius = 7.5;
      }

      // De-conflict exact overlapping coordinates using subtle radial displacement
      const coordKey = `${ev.latitude.toFixed(4)}_${ev.longitude.toFixed(4)}`;
      const hitCount = coordCounts[coordKey] || 0;
      coordCounts[coordKey] = hitCount + 1;

      let plotLat = ev.latitude;
      let plotLon = ev.longitude;
      if (hitCount > 0) {
        const angle = (hitCount * 2 * Math.PI) / 6;
        const offset = 0.00028 * Math.ceil(hitCount / 6);
        plotLat += offset * Math.cos(angle);
        plotLon += offset * Math.sin(angle);
      }

      const marker = L.circleMarker([plotLat, plotLon], {
        pane: 'observationsPane',
        radius,
        fillColor: color,
        color: '#FFFFFF',
        weight: 2,
        opacity: 0.95,
        fillOpacity: 0.85,
        bubblingMouseEvents: false,
      });

      const eventKey = ev.source_event_id || 'obs';
      const safeExtra = encodeURIComponent(JSON.stringify(ev));

      const popupHtml = `
        <div style="font-family: Inter, sans-serif; font-size: 11px; width: 270px; background: #0D131F; color: #E2E8F0; border-radius: 8px; overflow: hidden; border: 1px solid #2A374D;">
          <div style="padding: 10px 12px 8px; background: #070A10; border-bottom: 1px solid #1E293B;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 9px; font-weight: 800; font-family: monospace; letter-spacing: 0.05em; color: ${color}; background: ${color}20; padding: 2px 6px; border-radius: 4px; border: 1px solid ${color}40;">
                ${ev.final_risk_level.toUpperCase()} ANOMALY
              </span>
              <span style="font-size: 10px; color: #94A3B8; font-family: monospace;">
                FRP: ${ev.max_frp ? ev.max_frp.toFixed(1) : 'N/A'} MW
              </span>
            </div>
            <div style="font-size: 12px; font-weight: 700; color: #FFFFFF; font-family: monospace;">
              ${eventKey}
            </div>
            <div style="font-size: 10px; color: #94A3B8; font-family: monospace; margin-top: 2px;">
              ${ev.latitude.toFixed(4)}°N, ${ev.longitude.toFixed(4)}°E · ${ev.region_name || 'Corridor'}
            </div>
          </div>

          <div style="padding: 10px 12px; display: flex; flex-direction: column; gap: 6px;">
            <div style="display: flex; justify-content: space-between; font-size: 10px;">
              <span style="color: #94A3B8;">Observation Start:</span>
              <span style="font-family: monospace; color: #FFFFFF;">${ev.event_start ? ev.event_start.slice(0, 16).replace('T', ' ') : 'N/A'} UTC</span>
            </div>
            ${
              ev.nearest_industry_name
                ? `<div style="background: #121927; padding: 6px 8px; border-radius: 4px; border: 1px solid #1E293B;">
                    <div style="color: #94A3B8; font-size: 9px; text-transform: uppercase;">Nearest Infrastructure:</div>
                    <div style="font-weight: 600; color: #F59E0B; font-size: 11px;">${ev.nearest_industry_name}</div>
                    <div style="font-size: 10px; color: #94A3B8;">${ev.distance_to_nearest_industry_m ? Math.round(ev.distance_to_nearest_industry_m) + 'm' : ''} (${ev.nearest_industry_type || 'Industrial'})</div>
                  </div>`
                : ''
            }
            <div style="display: flex; justify-content: space-between; font-size: 10px;">
              <span style="color: #94A3B8;">Isolation Forest:</span>
              <span style="font-weight: 600; color: ${ev.iforest_agreement ? '#10B981' : '#94A3B8'};">
                ${ev.iforest_agreement ? 'Confirmed Anomaly' : 'Baseline Envelope'}
              </span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 4px;">
              <div style="display: flex; gap: 4px;">
                <button
                  onclick="window.__kratos_ask_ai__('observation', '${eventKey}', '${eventKey}', ${ev.latitude}, ${ev.longitude}, '${safeExtra}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 5px 8px; background: #F59E0B; color: #070A10; font-weight: 700; font-size: 10px; border-radius: 4px; border: none; cursor: pointer;"
                >
                  <span>Ask AI Investigator</span>
                </button>
                <button
                  onclick="window.__kratos_zoom_to__(${ev.latitude}, ${ev.longitude}, 16)"
                  style="padding: 5px 8px; background: #1E293B; color: #E2E8F0; font-size: 10px; font-weight: 600; border-radius: 4px; border: 1px solid #334155; cursor: pointer;"
                >
                  Zoom
                </button>
              </div>
              <div style="display: flex; gap: 4px;">
                <button
                  onclick="window.__kratos_generate_report__('feature', 'observation', '${eventKey}', '${ev.region_name || 'Corridor'}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 3px; padding: 5px 8px; background: #0F172A; color: #38BDF8; font-weight: 600; font-size: 9.5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.4); cursor: pointer;"
                >
                  <span>Investigation Report</span>
                </button>
                <button
                  onclick="window.__kratos_create_followup__('observation', '${eventKey}', 'Observation ${eventKey}', '${ev.region_name || 'Corridor'}')"
                  style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 3px; padding: 5px 8px; background: #0F172A; color: #F59E0B; font-weight: 600; font-size: 9.5px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.4); cursor: pointer;"
                >
                  <span>Create Follow-up</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { maxWidth: 300, className: 'kratos-custom-popup' });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        setSelectedFeature({
          type: 'observation',
          id: eventKey,
          name: `Anomaly ${eventKey}`,
          latitude: ev.latitude,
          longitude: ev.longitude,
          regionName: ev.region_name,
          properties: ev,
          association: ev.nearest_industry_name ? {
            nearestFacilityName: ev.nearest_industry_name,
            nearestCategory: ev.nearest_industry_type,
            distanceM: ev.distance_to_nearest_industry_m,
          } : undefined,
        });
        if (onSelectEvent) onSelectEvent(ev);
      });

      marker.addTo(layer);
    });
  }, [events, onSelectEvent, showObservations, setSelectedFeature]);

  // 6. Render OSM Facility Overlays
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = facilitiesLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();

    const getCategoryStyle = (category: string) => {
      switch (category) {
        case 'refinery':
          return { color: '#EC4899', fill: '#BE185D', label: 'Refinery' };
        case 'power_plant':
          return { color: '#F59E0B', fill: '#B45309', label: 'Power Plant' };
        case 'substation':
          return { color: '#8B5CF6', fill: '#6D28D9', label: 'Substation' };
        case 'mining_quarry':
          return { color: '#78716C', fill: '#44403C', label: 'Mines / Quarry' };
        case 'industrial':
        default:
          return { color: '#2563EB', fill: '#1D4ED8', label: 'Industrial Facility' };
      }
    };

    facilities.forEach((feat) => {
      const cat = feat.properties.facility_category;
      if (cat === 'industrial' && !showIndustrial) return;
      if ((cat === 'power_plant' || cat === 'substation') && !showPower) return;
      if (cat === 'refinery' && !showRefinery) return;
      if (cat === 'mining_quarry' && !showMining) return;

      const style = getCategoryStyle(cat);
      const props = feat.properties;
      const safeExtra = encodeURIComponent(JSON.stringify(props));

      // Resolve actual coordinate for facility
      let fLat = selectedRegion?.center ? selectedRegion.center[0] : 15.2;
      let fLon = selectedRegion?.center ? selectedRegion.center[1] : 76.6;
      if (feat.geometry) {
        if (feat.geometry.type === 'Point' && Array.isArray(feat.geometry.coordinates)) {
          fLon = feat.geometry.coordinates[0];
          fLat = feat.geometry.coordinates[1];
        } else if (feat.geometry.type === 'Polygon' && Array.isArray(feat.geometry.coordinates?.[0]?.[0])) {
          fLon = feat.geometry.coordinates[0][0][0];
          fLat = feat.geometry.coordinates[0][0][1];
        }
      }

      const popupHtml = `
        <div style="font-family: Inter, sans-serif; font-size: 11px; width: 260px; background: #0D131F; color: #E2E8F0; border-radius: 8px; overflow: hidden; border: 1px solid #2A374D;">
          <div style="padding: 10px 12px 8px; background: #070A10; border-bottom: 1px solid #1E293B;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 800; color: ${style.color}; text-transform: uppercase; font-size: 9px; font-family: monospace;">
                ${style.label}
              </span>
              <span style="color: #64748B; font-family: monospace; font-size: 9px;">
                ${props.osm_type} #${props.osm_id}
              </span>
            </div>
            <div style="color: #FFFFFF; font-weight: 700; font-size: 12px;">
              ${props.name}
            </div>
            ${props.subcategory ? `<div style="color: #94A3B8; font-size: 10px; margin-top: 2px;">Type: <span style="color: #E2E8F0;">${props.subcategory}</span></div>` : ''}
            ${props.region_name ? `<div style="color: #94A3B8; font-size: 10px;">Region: ${props.region_name}</div>` : ''}
          </div>

          <div style="padding: 10px 12px; display: flex; flex-direction: column; gap: 6px;">
            <div style="padding: 4px 6px; background: #121927; border-radius: 4px; font-size: 9px; color: #94A3B8; border-left: 2px solid ${style.color};">
              OSM Infrastructure Reference &mdash; not a confirmed heat anomaly
            </div>

            <div style="display: flex; gap: 4px; margin-top: 4px;">
              <button
                onclick="window.__kratos_ask_ai__('facility', '${props.osm_id}', '${(props.name || 'Facility').replace(/'/g, "\\'")}', ${fLat}, ${fLon}, '${safeExtra}')"
                style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 6px 8px; background: #1E293B; color: #F59E0B; font-weight: 700; font-size: 10px; border-radius: 4px; border: 1px solid #2A374D; cursor: pointer;"
              >
                <span>Ask AI About Facility</span>
              </button>
              <button
                onclick="window.__kratos_create_followup__('facility', '${props.osm_id}', '${(props.name || 'Facility').replace(/'/g, "\\'")}', '${props.region_name || 'Corridor'}')"
                style="padding: 6px 8px; background: #0F172A; color: #38BDF8; font-weight: 600; font-size: 10px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.4); cursor: pointer;"
              >
                Follow-up
              </button>
            </div>
          </div>
        </div>
      `;

      try {
        const geoLayer = L.geoJSON(feat as any, {
          pane: 'facilitiesPane',
          style: () => ({
            color: style.color,
            weight: 1.5,
            fillColor: style.fill,
            fillOpacity: 0.35,
          }),
          pointToLayer: (_point, latlng) => {
            return L.circleMarker(latlng, {
              pane: 'facilitiesPane',
              radius: 6,
              fillColor: style.fill,
              color: '#FFFFFF',
              weight: 1.5,
              opacity: 0.9,
              fillOpacity: 0.85,
              bubblingMouseEvents: false,
            });
          },
          onEachFeature: (_feature, lyr) => {
            lyr.on('click', (e) => {
              L.DomEvent.stopPropagation(e);
              setSelectedFeature({
                type: 'facility',
                id: String(props.osm_id || feat.id),
                name: props.name || 'Industrial Facility',
                latitude: fLat,
                longitude: fLon,
                regionName: props.region_name || selectedRegion?.name,
                properties: props,
                association: {
                  nearestFacilityName: props.name || 'Industrial Facility',
                  nearestCategory: props.facility_category,
                  distanceM: 0,
                  relationship: 'Direct Co-location',
                },
              });
            });
          },
        });

        geoLayer.bindPopup(popupHtml, { maxWidth: 280, className: 'kratos-custom-popup' });
        geoLayer.addTo(layer);
      } catch (e) {
        console.warn('Failed rendering OSM facility geometry:', feat.id, e);
      }
    });
  }, [facilities, showIndustrial, showPower, showRefinery, showMining, selectedRegion, setSelectedFeature]);

  // 7. Render Region Boundaries
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = regionsLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    if (!showRegions) return;

    regions.forEach((region) => {
      const [minLon, minLat, maxLon, maxLat] = region.bbox;
      const isSelected = selectedRegion?.id === region.id;
      const isIndustrial = region.category === 'industrial_corridor';

      const bounds: L.LatLngBoundsExpression = [
        [minLat, minLon],
        [maxLat, maxLon],
      ];

      const color = isSelected ? '#F59E0B' : isIndustrial ? '#3B82F6' : '#10B981';

      const rect = L.rectangle(bounds, {
        color,
        weight: isSelected ? 2.5 : 1.2,
        fillColor: color,
        fillOpacity: isSelected ? 0.15 : 0.05,
        dashArray: isSelected ? undefined : '4, 4',
      });

      rect.bindTooltip(
        `<div class="text-[11px] font-sans font-semibold">${region.name} (${region.state})</div>`,
        { permanent: false, direction: 'top', className: 'dark-tooltip' }
      );

      rect.on('click', () => {
        if (onSelectRegion) onSelectRegion(region);
      });

      rect.addTo(layer);
    });
  }, [regions, selectedRegion, onSelectRegion, showRegions]);

  // 8. Fly to Selected Region or Overview
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (selectedRegion) {
      map.flyTo(selectedRegion.center, selectedRegion.zoom, { duration: 1.2 });
    } else {
      map.flyTo([21.5, 80.0], 5, { duration: 1.2 });
    }
  }, [selectedRegion]);

  // 9. Fly to Selected Feature when selected externally (e.g. from DetectionTable, Global Search)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedFeature) return;
    if (selectedFeature.latitude && selectedFeature.longitude) {
      map.flyTo([selectedFeature.latitude, selectedFeature.longitude], Math.max(map.getZoom(), 15), { duration: 1.0 });
    }
  }, [selectedFeature]);

  return (
    <div className="relative w-full h-full min-h-[460px] rounded-lg overflow-hidden border border-[#1E293B] shadow-2xl bg-[#090E17]">
      <div ref={mapContainerRef} className="w-full h-full z-10" />

      {/* TOP-LEFT: MULTI-BASEMAP SELECTOR TOOLBAR */}
      <div className="absolute top-3 left-3 z-20 flex items-center gap-1 bg-[#0D131F]/90 backdrop-blur-md p-1 rounded-lg border border-[#2A374D] shadow-2xl">
        {(
          [
            { id: 'satellite', label: 'Satellite', icon: '🛰️' },
            { id: 'hybrid', label: 'Hybrid', icon: '🌐' },
            { id: 'street', label: 'Street', icon: '🗺️' },
            { id: 'dark', label: 'Dark', icon: '🌑' },
            { id: 'light', label: 'Light', icon: '☀️' },
            { id: 'terrain', label: 'Terrain', icon: '⛰️' },
          ] as const
        ).map((b) => (
          <button
            key={b.id}
            onClick={() => setActiveBasemap(b.id)}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded text-[11px] font-mono font-medium transition-all ${
              activeBasemap === b.id
                ? 'bg-[#F59E0B] text-slate-950 font-bold shadow-md shadow-[#F59E0B]/20'
                : 'text-[#94A3B8] hover:text-white hover:bg-[#1E293B]'
            }`}
            title={`Switch to ${b.label} basemap`}
          >
            <span>{b.icon}</span>
            <span className="hidden sm:inline">{b.label}</span>
          </button>
        ))}
      </div>

      {/* TOP-RIGHT: MAP OVERLAYS CONTROLS & COUNTS */}
      <div className="absolute top-3 right-3 z-20 select-none">
        <div className="bg-[#0D131F]/90 backdrop-blur-md rounded-lg border border-[#2A374D] shadow-2xl overflow-hidden transition-all">
          <button
            onClick={() => setIsLayerPanelOpen(!isLayerPanelOpen)}
            className="w-full flex items-center justify-between gap-3 px-3 py-2 text-xs font-mono font-bold text-white hover:bg-[#1E293B] transition-colors"
          >
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span className="uppercase tracking-wider">Layers</span>
            </div>
            {isLoadingFacilities ? (
              <span className="text-[9px] text-[#F59E0B] font-normal animate-pulse">Loading OSM...</span>
            ) : (
              <span className="text-[10px] text-slate-400 font-normal">
                {isLayerPanelOpen ? 'Hide' : 'Show'}
              </span>
            )}
          </button>

          {isLayerPanelOpen && (
            <div className="p-3 pt-1 border-t border-[#1E293B] space-y-2 text-[11px] max-h-[360px] overflow-y-auto">
              <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showClusters}
                    onChange={(e) => setShowClusters(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-600 text-[#F59E0B] focus:ring-0 w-3.5 h-3.5"
                  />
                  <span className="w-2.5 h-2.5 rotate-45 bg-[#F59E0B] border border-white inline-block" />
                  <span>Persistent Clusters</span>
                </div>
                <span className="text-[10px] font-mono text-[#F59E0B]">({sources.length})</span>
              </label>

              <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showObservations}
                    onChange={(e) => setShowObservations(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-600 text-red-500 focus:ring-0 w-3.5 h-3.5"
                  />
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
                  <span>Thermal Anomalies</span>
                </div>
                <span className="text-[10px] font-mono text-red-400">({events.length})</span>
              </label>

              <div className="pt-1.5 border-t border-[#1E293B]">
                <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono mb-1">
                  OSM Infrastructure
                </div>

                <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white py-0.5">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={showIndustrial}
                      onChange={(e) => setShowIndustrial(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-600 text-blue-500 focus:ring-0 w-3.5 h-3.5"
                    />
                    <span className="w-2.5 h-2.5 rounded bg-blue-500 inline-block" />
                    <span>Industrial Works</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">({facilityCounts['industrial'] || 0})</span>
                </label>

                <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white py-0.5">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={showPower}
                      onChange={(e) => setShowPower(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-600 text-amber-500 focus:ring-0 w-3.5 h-3.5"
                    />
                    <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block" />
                    <span>Power & Substation</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    ({(facilityCounts['power_plant'] || 0) + (facilityCounts['substation'] || 0)})
                  </span>
                </label>

                <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white py-0.5">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={showRefinery}
                      onChange={(e) => setShowRefinery(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-600 text-pink-500 focus:ring-0 w-3.5 h-3.5"
                    />
                    <span className="w-2.5 h-2.5 rounded bg-pink-500 inline-block" />
                    <span>Refineries</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">({facilityCounts['refinery'] || 0})</span>
                </label>

                <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white py-0.5">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={showMining}
                      onChange={(e) => setShowMining(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-600 text-stone-400 focus:ring-0 w-3.5 h-3.5"
                    />
                    <span className="w-2.5 h-2.5 rounded bg-stone-400 inline-block" />
                    <span>Mines & Quarries</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">({facilityCounts['mining_quarry'] || 0})</span>
                </label>
              </div>

              <label className="flex items-center justify-between gap-3 cursor-pointer text-[#E2E8F0] hover:text-white pt-1.5 border-t border-[#1E293B]">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showRegions}
                    onChange={(e) => setShowRegions(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-600 text-emerald-500 focus:ring-0 w-3.5 h-3.5"
                  />
                  <span className="w-2.5 h-2 border border-blue-400 inline-block" />
                  <span>Region Boundaries</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">({regions.length})</span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM-RIGHT: SURVEILLANCE LEGEND */}
      <div className="absolute bottom-4 right-4 z-20 bg-[#0D131F]/90 backdrop-blur-md p-3 rounded-lg border border-[#2A374D] shadow-2xl text-xs select-none">
        <div className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider mb-2 font-mono flex items-center justify-between">
          <span>Surveillance Symbology</span>
        </div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rotate-45 bg-[#F59E0B] border border-white" />
            <span className="text-[#E2E8F0]">Persistent Heat Cluster</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 border border-white" />
            <span className="text-[#E2E8F0]">Critical Exceedance Anomaly</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            <span className="text-[#94A3B8]">High Risk Observation</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
            <span className="text-[#94A3B8]">Medium Risk Observation</span>
          </div>
          <div className="pt-1.5 mt-1.5 border-t border-[#1E293B] space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-3 h-2 border border-blue-400 bg-blue-500/20" />
              <span className="text-[#94A3B8]">Industrial Boundary</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-2 border border-pink-400 bg-pink-500/20" />
              <span className="text-[#94A3B8]">Refinery / Petrochemical</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-2 border border-emerald-400 bg-emerald-500/20" />
              <span className="text-[#94A3B8]">Forest Landscape</span>
            </div>
          </div>
        </div>
      </div>

      {/* NATIVE ZOOM DETAIL INDICATOR */}
      {currentZoom > BASEMAP_ZOOM_CONFIG[activeBasemap].maxNativeZoom && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-3.5 py-1.5 rounded-full bg-[#0D131F]/95 border border-[#F59E0B]/50 text-white text-[11px] font-mono shadow-2xl backdrop-blur flex items-center gap-2 pointer-events-none animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-[#F59E0B] animate-ping" />
          <span>Maximum native imagery detail reached (zoom {currentZoom}). Scaling last available capture.</span>
        </div>
      )}
    </div>
  );
};
