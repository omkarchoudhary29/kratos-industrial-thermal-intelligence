import React, { useEffect, useState } from 'react';
import {
  Cpu,
  ShieldCheck,
  Database,
  Server,
  RefreshCw,
  CheckCircle2,
  Users,
  Sliders,
  History,
  Lock,
  AlertTriangle,
  Save,
} from 'lucide-react';
import { api } from '../services/api';
import { SystemStatus } from '../types';

interface SettingsViewProps {
  status?: SystemStatus | null;
}

export const SettingsView: React.FC<SettingsViewProps> = () => {
  const [profile, setProfile] = useState<any | null>(null);
  const [thresholds, setThresholds] = useState<any | null>(null);
  const [modelSettings, setModelSettings] = useState<any | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingThresholds, setSavingThresholds] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    fetchSettingsData();
  }, []);

  const fetchSettingsData = async () => {
    try {
      setLoading(true);
      const [prof, thresh, model, logs] = await Promise.all([
        api.getUserProfile(),
        api.getMonitoringSettings(),
        api.getModelSettings(),
        api.getAuditLogs({ limit: 15 }),
      ]);
      setProfile(prof);
      setThresholds(thresh);
      setModelSettings(model);
      setAuditLogs(logs.logs || []);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveThresholds = async () => {
    if (!thresholds) return;
    try {
      setSavingThresholds(true);
      setSaveSuccess(false);
      await api.updateMonitoringSettings(thresholds);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      fetchSettingsData();
    } catch (err) {
      console.error('Failed to update thresholds:', err);
    } finally {
      setSavingThresholds(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center bg-white border border-slate-200 rounded-xl space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        <div className="text-xs font-mono text-slate-500">Loading system administration & RBAC settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              Settings & Platform Administration
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Role-Based Access Control (RBAC), operational threshold configuration, machine learning telemetry, and tamper-evident audit logs.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="badge bg-emerald-50 text-emerald-800 border-emerald-200 flex items-center gap-1.5 font-bold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>OPERATIONAL HEALTHY</span>
          </span>
        </div>
      </div>

      {/* User Profile & RBAC Roles */}
      {profile && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <span>Active User Profile & Role-Based Access Control (RBAC)</span>
            </h3>
            <span className="badge badge-gold font-mono text-[10px]">{profile.role}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {(profile.available_roles || []).map((r: any) => {
              const isCurrent = r.role_key === (profile.role === 'Administrator' ? 'ADMINISTRATOR' : 'MONITORING_ANALYST');
              return (
                <div
                  key={r.role_key}
                  className={`p-3 rounded-xl border text-xs space-y-1.5 transition-all ${
                    isCurrent
                      ? 'bg-blue-50/50 border-blue-400 ring-2 ring-blue-100'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex justify-between items-center font-bold">
                    <span className="text-slate-900">{r.display_name}</span>
                    {isCurrent && <span className="badge bg-blue-600 text-white text-[9px]">Active</span>}
                  </div>
                  <p className="text-[10px] text-slate-500 leading-relaxed">{r.description}</p>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {r.permissions.map((p: string) => (
                      <span key={p} className="text-[9px] font-mono bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-600">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Operational Thresholds Form */}
      {thresholds && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
                <Sliders className="w-4 h-4 text-blue-600" />
                <span>Operational Monitoring & Alert Thresholds</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Configures automated triage scoring cutoffs and notification dispatch criteria.</p>
            </div>
            {saveSuccess && (
              <span className="badge bg-emerald-50 text-emerald-800 border-emerald-200 flex items-center gap-1 text-[11px] font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Saved to System Audit</span>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">High FRP Alert Threshold (MW):</label>
              <input
                type="number"
                step="0.5"
                value={thresholds.high_frp_threshold_mw || 15.0}
                onChange={(e) => setThresholds({ ...thresholds, high_frp_threshold_mw: parseFloat(e.target.value) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Critical FRP Cutoff (MW):</label>
              <input
                type="number"
                step="0.5"
                value={thresholds.critical_frp_threshold_mw || 35.0}
                onChange={(e) => setThresholds({ ...thresholds, critical_frp_threshold_mw: parseFloat(e.target.value) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Persistence Days Threshold:</label>
              <input
                type="number"
                value={thresholds.persistence_day_threshold || 3}
                onChange={(e) => setThresholds({ ...thresholds, persistence_day_threshold: parseInt(e.target.value, 10) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Spatial Cluster Radius (m):</label>
              <input
                type="number"
                value={thresholds.spatial_cluster_eps_m || 300.0}
                onChange={(e) => setThresholds({ ...thresholds, spatial_cluster_eps_m: parseFloat(e.target.value) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Facility Buffer Radius (m):</label>
              <input
                type="number"
                value={thresholds.facility_buffer_radius_m || 2000.0}
                onChange={(e) => setThresholds({ ...thresholds, facility_buffer_radius_m: parseFloat(e.target.value) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Default Baseline Window (Days):</label>
              <input
                type="number"
                value={thresholds.default_timeline_window_days || 30}
                onChange={(e) => setThresholds({ ...thresholds, default_timeline_window_days: parseInt(e.target.value, 10) })}
                className="w-full p-2 border border-slate-300 rounded-lg bg-white"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSaveThresholds}
              disabled={savingThresholds}
              className="py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-2 shadow-xs transition-colors"
            >
              {savingThresholds ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>Save Monitoring Thresholds</span>
            </button>
          </div>
        </div>
      )}

      {/* Model Administration & Feature Telemetry */}
      {modelSettings && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-600" />
              <span>Machine Learning Model Telemetry (16 Physical & Geospatial Features)</span>
            </h3>
            <span className="badge badge-gold font-mono text-[10px]">{modelSettings.model_version}</span>
          </div>

          <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl flex items-start gap-2.5 text-xs text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong>Ground-Truth Integrity Notice:</strong> {modelSettings.proxy_label_disclaimer}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
            {(modelSettings.features || []).map((feat: string, idx: number) => (
              <div key={feat} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700">
                <span className="text-slate-400 mr-1.5">{idx + 1}.</span>
                <strong>{feat}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tamper-Evident System Audit Logs */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex justify-between items-center pb-2 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
              <History className="w-4 h-4 text-slate-600" />
              <span>Tamper-Evident System Audit Trail</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">Immutable record of logins, report approvals, authority submissions, and configuration changes.</p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">PostgreSQL 18 Table</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 font-mono text-slate-600 text-[11px]">
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Actor / User</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Action Type</th>
                <th className="py-2.5 px-3">Target Resource</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-slate-400">No audit logs recorded yet.</td>
                </tr>
              ) : (
                auditLogs.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50/80">
                    <td className="py-2 px-3 text-slate-500">{l.timestamp ? new Date(l.timestamp).toLocaleString() : 'Recent'}</td>
                    <td className="py-2 px-3 font-semibold text-slate-900">{l.username}</td>
                    <td className="py-2 px-3 text-slate-600">{l.user_role}</td>
                    <td className="py-2 px-3 font-bold text-blue-700">{l.action_type}</td>
                    <td className="py-2 px-3 text-slate-600">{l.resource_type} ({l.resource_id})</td>
                    <td className="py-2 px-3 text-right">
                      <span className="badge bg-emerald-50 text-emerald-800 border-emerald-200 text-[10px]">{l.status}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
