import React from 'react';
import { Layers, MapPin, Users, Globe2, Building2 } from 'lucide-react';
import { Region } from '../types';

interface SpatialContextViewProps {
  selectedRegion: Region | null;
}

export const SpatialContextView: React.FC<SpatialContextViewProps> = ({ selectedRegion }) => {
  const worldCoverClasses = [
    { code: 10, name: 'Tree cover', group: 'forest', color: 'bg-emerald-600', desc: 'Closed and open evergreen / deciduous forest canopy' },
    { code: 20, name: 'Shrubland', group: 'vegetation', color: 'bg-amber-600', desc: 'Woody vegetation with height under 2 meters' },
    { code: 30, name: 'Grassland', group: 'vegetation', color: 'bg-lime-500', desc: 'Natural herbaceous cover and pasture' },
    { code: 40, name: 'Cropland', group: 'agriculture', color: 'bg-yellow-400', desc: 'Cultivated lands, paddy fields, harvest cycles' },
    { code: 50, name: 'Built-up', group: 'built_up', color: 'bg-red-500', desc: 'Industrial complexes, settlements, concrete infrastructure' },
    { code: 60, name: 'Bare / sparse vegetation', group: 'bare', color: 'bg-stone-500', desc: 'Open mines, quarry rocks, unpaved terrain' },
    { code: 80, name: 'Permanent water bodies', group: 'water', color: 'bg-blue-500', desc: 'Reservoirs, cooling ponds, rivers' },
  ];

  const exposureBands = [
    { radius: '1 km', label: 'Immediate Vicinity', description: 'Immediate perimeter zone sensitive to smoke inhalation and direct radiant heat' },
    { radius: '3 km', label: 'Tactical Evacuation Ring', description: 'Surrounding buffer for secondary industrial hazards and road disruption' },
    { radius: '5 km', label: 'Regional Impact Radius', description: 'Wider population exposure zone evaluated using WorldPop India 2026 grids' },
  ];

  return (
    <div className="space-y-6">
      <div className="industrial-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-5 h-5 text-[#F59E0B]" />
            <h2 className="text-base font-bold text-white uppercase font-mono">
              Geospatial Intelligence & Multi-Layer Context
            </h2>
          </div>
          <p className="text-xs text-[#94A3B8]">
            Enriching raw satellite pixels with high-resolution land classification, industrial infrastructure, and census-grounded exposure metrics.
          </p>
        </div>

        {selectedRegion && (
          <div className="p-2.5 rounded bg-[#0D131F] border border-[#2A374D] text-xs font-mono">
            <span className="text-[#64748B] block text-[10px]">ACTIVE WORKSPACE</span>
            <span className="text-[#F59E0B] font-bold">{selectedRegion.name}</span>
            <span className="text-[#94A3B8] block text-[10px]">Bounding Box: {selectedRegion.bbox.map((v) => v.toFixed(2)).join(', ')}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ESA WorldCover Card */}
        <div className="industrial-card p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1E293B] pb-3">
            <Globe2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold text-white uppercase font-mono">
              ESA WorldCover 10m Land Classification
            </h3>
          </div>
          <p className="text-xs text-[#94A3B8]">
            Sentinel-1 and Sentinel-2 derived 10-meter land cover enrichment. Automatically categorizes anomaly pixels to distinguish built-up factories from agricultural burning or forest fires.
          </p>

          <div className="space-y-2">
            {worldCoverClasses.map((item) => (
              <div
                key={item.code}
                className="flex items-center justify-between p-2 rounded bg-[#0D131F] border border-[#1E293B] text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className={`w-3 h-3 rounded-full ${item.color}`} />
                  <span className="text-[#E2E8F0] font-medium">{item.name}</span>
                </div>
                <span className="text-[10px] font-mono text-[#64748B]">
                  Class {item.code} · {item.group}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Population Exposure & OSM Infrastructure */}
        <div className="space-y-4">
          {/* Population exposure */}
          <div className="industrial-card p-5 space-y-3">
            <div className="flex items-center gap-2 border-b border-[#1E293B] pb-3">
              <Users className="w-4 h-4 text-[#F59E0B]" />
              <h3 className="text-xs font-bold text-white uppercase font-mono">
                WorldPop 2026 Population Exposure Radii
              </h3>
            </div>
            <p className="text-xs text-[#94A3B8]">
              Automated spatial aggregation across cumulative exposure rings around priority industrial anomalies.
            </p>

            <div className="space-y-2">
              {exposureBands.map((band) => (
                <div key={band.radius} className="p-2.5 rounded bg-[#0D131F] border border-[#1E293B]">
                  <div className="flex justify-between items-center text-xs font-mono font-bold text-white">
                    <span>{band.label}</span>
                    <span className="text-[#F59E0B]">{band.radius}</span>
                  </div>
                  <p className="text-[11px] text-[#64748B] mt-0.5">{band.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* OSM Industrial Infrastructure */}
          <div className="industrial-card p-5 space-y-3">
            <div className="flex items-center gap-2 border-b border-[#1E293B] pb-3">
              <Building2 className="w-4 h-4 text-blue-400" />
              <h3 className="text-xs font-bold text-white uppercase font-mono">
                OpenStreetMap Industrial Facility Context
              </h3>
            </div>
            <p className="text-xs text-[#94A3B8]">
              Continuous spatial joins against steelworks, thermal power stations, chemical plants, petroleum refineries, and blast furnace complexes.
            </p>
            <div className="flex items-center justify-between text-xs font-mono text-[#64748B] pt-2 border-t border-[#1E293B]">
              <span>Facility Distance Threshold:</span>
              <span className="text-white font-semibold">1,000 meters</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
