import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  accent?: 'gold' | 'critical' | 'high' | 'medium' | 'low' | 'blue' | 'default';
  meta?: string;
  tooltip?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  accent = 'default',
  meta,
  tooltip,
}) => {
  const accentBadge = {
    gold: 'bg-amber-50 text-amber-700 border-amber-200',
    critical: 'bg-red-50 text-red-700 border-red-200',
    high: 'bg-orange-50 text-orange-700 border-orange-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    default: 'bg-slate-100 text-slate-700 border-slate-200',
  };

  const textStyles = {
    gold: 'text-amber-600',
    critical: 'text-red-600',
    high: 'text-orange-600',
    medium: 'text-amber-600',
    low: 'text-emerald-600',
    blue: 'text-blue-600',
    default: 'text-slate-900',
  };

  return (
    <div
      title={tooltip || subtitle}
      className="bg-white border border-slate-200 rounded-xl p-4 relative overflow-hidden shadow-xs hover:border-slate-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5 font-bold tracking-wide uppercase font-mono">
        <span>{title}</span>
        {icon && (
          <span className={`p-1.5 rounded-lg border ${accentBadge[accent]}`}>
            {icon}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold font-mono tracking-tight ${textStyles[accent]}`}>
          {value}
        </span>
        {meta && (
          <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            {meta}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">
          {subtitle}
        </p>
      )}
    </div>
  );
};
