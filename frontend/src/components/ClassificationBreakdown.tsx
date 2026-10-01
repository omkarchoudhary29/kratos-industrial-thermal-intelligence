import React from 'react';
import {
  Flame,
  Factory,
  Wheat,
  Pickaxe,
  Trees,
  Cog,
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export const ClassificationBreakdown: React.FC = () => {
  const classes = [
    {
      id: 'industrial_fire',
      name: 'Industrial Fire',
      icon: <Flame className="w-5 h-5 text-red-500" />,
      color: 'border-red-500/40 bg-red-500/10 text-red-400',
      rule: 'High anomaly score + inside industrial boundary + non-stationary thermal expansion + FRP > 3x historical baseline.',
      evidence: ['FRP jump > 300%', 'Built-up / Industrial land cover', 'Absence of gas flare structure', 'Rapid multi-pixel growth'],
    },
    {
      id: 'gas_flare',
      name: 'Gas Flare',
      icon: <Flame className="w-5 h-5 text-orange-500" />,
      color: 'border-orange-500/40 bg-orange-500/10 text-orange-400',
      rule: 'Highly localized stationary cluster (<100m) + persistent high temperature across night & day passes + oil/gas refinery proximity.',
      evidence: ['High night-time brightness temperature', 'Continuous 30-day persistence > 70%', 'Proximity to flare stack OSM tag', 'Low spatial spread'],
    },
    {
      id: 'agricultural_burning',
      name: 'Agricultural Residue Burning',
      icon: <Wheat className="w-5 h-5 text-amber-400" />,
      color: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
      rule: 'Short-lived single-day episode + ESA WorldCover cropland class + seasonal harvest window alignment.',
      evidence: ['ESA WorldCover = Cropland (class 40)', 'Zero prior 30-day persistence', 'Day-time afternoon overpass (VIIRS N20)', 'Moderate FRP (<25 MW)'],
    },
    {
      id: 'mining_activity',
      name: 'Mining Activity / Spoil Pile Fire',
      icon: <Pickaxe className="w-5 h-5 text-yellow-500" />,
      color: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-400',
      rule: 'Within active opencast mine polygon or quarry buffer + smoldering coal seam characteristics + moderate persistent heat.',
      evidence: ['Inside OSM quarry / open pit boundary', 'Bare ground / sparse vegetation cover', 'Long duration (>14 days smoldering)', 'Low-to-moderate FRP'],
    },
    {
      id: 'wildfire',
      name: 'Wildfire / Forest Fire',
      icon: <Trees className="w-5 h-5 text-emerald-400" />,
      color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
      rule: 'Dense tree canopy or shrubland land cover + progressive front movement + dry season weather alignment.',
      evidence: ['ESA WorldCover = Tree cover (class 10)', 'Cluster propagation over consecutive overpasses', 'Distance to industrial corridor > 5 km', 'High flame front FRP'],
    },
    {
      id: 'industrial_process_heat',
      name: 'Industrial Process Heat (Normal)',
      icon: <Cog className="w-5 h-5 text-blue-400" />,
      color: 'border-blue-500/40 bg-blue-500/10 text-blue-400',
      rule: 'Within blast furnace, cement kiln, or metal smelter + FRP consistent with 4-year baseline mean + Isolation Forest normal range.',
      evidence: ['Isolation Forest score within normal boundary', 'FRP / baseline ratio between 0.8x and 1.2x', 'Active operating facility metadata', 'High annual recurrence'],
    },
    {
      id: 'unknown',
      name: 'Unclassified Thermal Anomaly',
      icon: <HelpCircle className="w-5 h-5 text-gray-400" />,
      color: 'border-gray-500/40 bg-gray-500/10 text-gray-400',
      rule: 'Ambiguous land-cover classification or contradictory spectral indicators requiring manual analyst verification.',
      evidence: ['Sub-threshold FRP observation', 'Cloud fringe contamination', 'Indeterminate land cover transition zone'],
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title & Methodology Banner */}
      <div className="industrial-card p-6 space-y-2 border-l-4 border-l-[#F59E0B]">
        <div className="flex items-center gap-2">
          <Factory className="w-5 h-5 text-[#F59E0B]" />
          <h2 className="text-base font-bold text-white uppercase font-mono tracking-wide">
            Explainable 7-Way Source Classification Engine
          </h2>
        </div>
        <p className="text-xs text-[#CBD5E1] leading-relaxed max-w-4xl">
          Rather than relying on an opaque deep-learning black box, the platform utilizes transparent, rule-grounded classification rules that integrate multi-sensor VIIRS satellite observations, 2021–2024 historical baseline statistics, ESA WorldCover land-use, and OpenStreetMap industrial infrastructure tags.
        </p>
      </div>

      {/* 7 Classification Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {classes.map((cls) => (
          <div
            key={cls.id}
            className="industrial-card p-4 space-y-3 flex flex-col justify-between hover:border-[#2A374D] transition-all"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded border ${cls.color}`}>
                    {cls.icon}
                  </div>
                  <h3 className="text-xs font-bold text-white uppercase font-mono">
                    {cls.name}
                  </h3>
                </div>
              </div>

              <div className="p-2.5 rounded bg-[#0D131F] border border-[#1E293B] text-[11px] text-[#94A3B8] mb-3">
                <span className="text-[10px] font-mono text-[#F59E0B] font-semibold uppercase block mb-1">
                  Primary Classification Rule
                </span>
                {cls.rule}
              </div>

              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-[#64748B] uppercase block">
                  Grounding Evidence Checklist
                </span>
                {cls.evidence.map((ev, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 text-[11px] text-[#CBD5E1]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span>{ev}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-[#1E293B] flex justify-between items-center text-[10px] font-mono text-[#64748B]">
              <span>ID: {cls.id}</span>
              <span className="text-emerald-400 font-semibold">RULE ACTIVE</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
