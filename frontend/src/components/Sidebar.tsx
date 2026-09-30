import React from 'react';
import {
  LayoutDashboard,
  Map as MapIcon,
  Factory,
  Trees,
  Search,
  Activity,
  Tags,
  Layers,
  FileText,
  MessageSquare,
  Users,
  Cpu,
  ClipboardCheck,
  Flame,
  ShieldAlert,
  FileSearch,
} from 'lucide-react';

export type ViewTab =
  | 'dashboard'
  | 'india_map'
  | 'thermal_analysis'
  | 'source_facility'
  | 'risk_prediction'
  | 'investigations'
  | 'ai_reports'
  | 'follow_ups'
  | 'analytics'
  | 'integrations'
  | 'settings'
  // Legacy / Direct Sub-Tab aliases
  | 'corridors'
  | 'forests'
  | 'detections'
  | 'persistent'
  | 'classifications'
  | 'spatial_context'
  | 'ai_chat'
  | 'field_reports';

interface SidebarProps {
  currentTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  unresolvedAlertsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  unresolvedAlertsCount = 0,
}) => {
  const navItems: Array<{
    id: ViewTab;
    label: string;
    icon: React.ReactNode;
    badge?: string | number;
  }> = [
    {
      id: 'dashboard',
      label: '1. Overview Monitoring',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      id: 'india_map',
      label: '2. Live Geospatial Map',
      icon: <MapIcon className="w-4 h-4" />,
    },
    {
      id: 'thermal_analysis',
      label: '3. Thermal Analysis & FRP',
      icon: <Flame className="w-4 h-4 text-amber-500" />,
    },
    {
      id: 'source_facility',
      label: '4. Source & Facility Intel',
      icon: <Factory className="w-4 h-4 text-blue-600" />,
      badge: '312',
    },
    {
      id: 'risk_prediction',
      label: '5. Risk & Prediction',
      icon: <ShieldAlert className="w-4 h-4 text-rose-600" />,
    },
    {
      id: 'investigations',
      label: '6. Incident Investigations',
      icon: <FileSearch className="w-4 h-4 text-indigo-600" />,
      badge: '12',
    },
    {
      id: 'ai_reports',
      label: '7. Intelligence Reports',
      icon: <FileText className="w-4 h-4" />,
      badge: 'AI',
    },
    {
      id: 'follow_ups',
      label: '8. Follow-up & Verification',
      icon: <ClipboardCheck className="w-4 h-4 text-emerald-600" />,
      badge: unresolvedAlertsCount > 0 ? unresolvedAlertsCount : 6,
    },
    {
      id: 'analytics',
      label: '9. Advanced Analytics',
      icon: <Activity className="w-4 h-4 text-purple-600" />,
      badge: '10',
    },
    {
      id: 'integrations',
      label: '10. Data & Integrations',
      icon: <Layers className="w-4 h-4 text-cyan-600" />,
      badge: '5',
    },
    {
      id: 'settings',
      label: '11. Settings & Admin',
      icon: <Cpu className="w-4 h-4 text-slate-700" />,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between select-none h-[calc(100vh-4rem)] flex-shrink-0 shadow-xs">
      <div className="py-4 px-2 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 tracking-wider uppercase font-mono">
          Surveillance Workspaces
        </div>
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-blue-50/80 text-blue-700 font-semibold border border-blue-200/80 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className={isActive ? 'text-blue-600' : 'text-slate-400'}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-md font-mono font-bold border ${
                    item.badge === 'AI'
                      ? 'bg-blue-100 text-blue-700 border-blue-200'
                      : isActive
                      ? 'bg-blue-100 text-blue-800 border-blue-300'
                      : 'bg-slate-100 text-slate-600 border-slate-200'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Info Box */}
      <div className="p-3 m-2 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-500 space-y-1">
        <div className="flex justify-between items-center text-slate-700 font-mono text-[10px]">
          <span>MODEL ENGINE</span>
          <span className="text-emerald-600 font-bold">IForest v1.0</span>
        </div>
        <p className="text-[10px] leading-tight text-slate-500">
          Unsupervised 16-feature anomaly inference with rule-based source classification.
        </p>
      </div>
    </aside>
  );
};
