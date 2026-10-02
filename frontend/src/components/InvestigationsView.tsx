import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  Clock,
  UserCheck,
  FileSearch,
  Building2,
  AlertTriangle,
  ChevronRight,
  Filter,
  Search,
  MessageSquare,
  Sparkles,
  MapPin,
  Flame,
  FileText,
} from 'lucide-react';
import { api } from '../services/api';
import { InvestigationItem, Region } from '../types';
import { useSelectedFeature } from '../context/SelectedFeatureContext';

interface InvestigationsViewProps {
  selectedRegion: Region | null;
  onOpenReportModal?: (scope: 'feature', featureType: string, featureId: string) => void;
  onInspectFeature?: (featureType: string, featureId: string, regionName?: string) => void;
}

export const InvestigationsView: React.FC<InvestigationsViewProps> = ({
  selectedRegion,
  onOpenReportModal,
  onInspectFeature,
}) => {
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [validStates, setValidStates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedInv, setSelectedInv] = useState<InvestigationItem | null>(null);

  // Status transition state
  const [transitionStatus, setTransitionStatus] = useState<string>('');
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [transitioning, setTransitioning] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const { setSelectedFeature, setIsChatOpen } = useSelectedFeature();

  useEffect(() => {
    fetchInvestigations();
  }, [selectedRegion]);

  const fetchInvestigations = async () => {
    try {
      setLoading(true);
      const res = await api.getInvestigations({
        region: selectedRegion?.name,
        limit: 30,
      });
      setInvestigations(res.investigations || []);
      setValidStates(res.valid_review_states || []);
      if (res.investigations && res.investigations.length > 0) {
        setSelectedInv(res.investigations[0]);
        setTransitionStatus(res.investigations[0].human_review_status);
      }
    } catch (err) {
      console.error('Failed to load investigations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectInvestigation = (inv: InvestigationItem) => {
    setSelectedInv(inv);
    setTransitionStatus(inv.human_review_status);
    setReviewerNotes('');
    setFeedbackMsg(null);

    // Sync to selected feature context
    setSelectedFeature({
      type: (inv.feature_type as any) || 'report',
      id: String(inv.feature_id || inv.id),
      name: inv.title,
      latitude: 23.5,
      longitude: 85.0,
      regionName: inv.region_name,
      properties: inv as any,
    });
  };

  const handleUpdateStatus = async () => {
    if (!selectedInv || !transitionStatus) return;
    try {
      setTransitioning(true);
      setFeedbackMsg(null);
      const res = await api.updateInvestigationStatus(
        selectedInv.id,
        transitionStatus,
        reviewerNotes
      );
      setFeedbackMsg(res.message);

      // Update local item
      const updated = { ...selectedInv, human_review_status: transitionStatus as any };
      setSelectedInv(updated);
      setInvestigations((prev) =>
        prev.map((item) => (item.id === selectedInv.id ? updated : item))
      );
    } catch (err: any) {
      console.error('Failed to update status:', err);
      setFeedbackMsg(`Error updating state: ${err.message}`);
    } finally {
      setTransitioning(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'Authority confirmed':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-100 text-purple-800 border border-purple-200">
            Authority Confirmed
          </span>
        );
      case 'Field verified':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            Field Verified
          </span>
        );
      case 'Field verification pending':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-200">
            Field Verification Pending
          </span>
        );
      case 'Analyst reviewed':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-800 border border-blue-200">
            Analyst Reviewed
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
            AI Assessment
          </span>
        );
    }
  };

  const filtered = investigations.filter((inv) => {
    if (statusFilter !== 'all' && inv.human_review_status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        inv.report_key.toLowerCase().includes(q) ||
        inv.title.toLowerCase().includes(q) ||
        inv.region_name.toLowerCase().includes(q) ||
        (inv.feature_id && inv.feature_id.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileSearch className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              AI-Assisted Incident Investigations & Review Workflow
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            5-tier human review lifecycle: AI assessment &rarr; Analyst reviewed &rarr; Field verification pending &rarr; Field verified &rarr; Authority confirmed.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-500">
            Region: <strong className="text-slate-800">{selectedRegion?.name || 'Pan-India Overview'}</strong>
          </span>
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-indigo-50 text-indigo-800 border border-indigo-200">
            {investigations.length} Active Dossiers
          </span>
        </div>
      </div>

      {/* Review Lifecycle Flow Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <div className="text-[10px] font-mono font-bold uppercase text-slate-400 mb-2">
          Investigation Review State Transition Machine
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-center">
            <div className="font-bold text-slate-700">1. AI Assessment</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Automated screening</div>
          </div>
          <div className="p-2.5 rounded-lg bg-blue-50/60 border border-blue-200 text-center">
            <div className="font-bold text-blue-700">2. Analyst Reviewed</div>
            <div className="text-[10px] text-blue-500 mt-0.5">Desk triage complete</div>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-50/60 border border-amber-200 text-center">
            <div className="font-bold text-amber-700">3. Field Pending</div>
            <div className="text-[10px] text-amber-500 mt-0.5">Inspection task assigned</div>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-center">
            <div className="font-bold text-emerald-700">4. Field Verified</div>
            <div className="text-[10px] text-emerald-500 mt-0.5">In-situ evidence logged</div>
          </div>
          <div className="p-2.5 rounded-lg bg-purple-50/60 border border-purple-200 text-center">
            <div className="font-bold text-purple-700">5. Authority Confirmed</div>
            <div className="text-[10px] text-purple-500 mt-0.5">Statutory SPCB notice</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search dossier key, incident title, target ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs"
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold text-slate-500 text-[11px]">Workflow State:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-slate-300 rounded px-2.5 py-1.5 bg-white text-xs text-slate-700"
          >
            <option value="all">All States</option>
            {validStates.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Queue & Investigation Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dossiers Queue (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex justify-between items-center text-xs text-slate-500 font-mono px-1">
            <span>Showing {filtered.length} active investigation dossiers</span>
            <span>Sorted by Incident Priority</span>
          </div>

          {loading ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-xs">
              Loading investigation records...
            </div>
          ) : filtered.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-xs">
              No investigations match the current filter.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
              {filtered.map((inv) => {
                const isSelected = selectedInv?.id === inv.id;
                return (
                  <div
                    key={inv.id}
                    onClick={() => handleSelectInvestigation(inv)}
                    className={`bg-white border rounded-xl p-4 cursor-pointer transition-all space-y-3 ${
                      isSelected
                        ? 'border-indigo-500 ring-2 ring-indigo-500/20 shadow-sm bg-indigo-50/15'
                        : 'border-slate-200 hover:border-slate-300 hover:shadow-xs'
                    }`}
                  >
                    <div className="flex flex-wrap justify-between items-start gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {inv.report_key}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.2 rounded bg-slate-100">
                            {inv.region_name}
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-slate-800 line-clamp-1">{inv.title}</h4>
                      </div>

                      <div className="flex items-center gap-2">
                        {getStatusBadge(inv.human_review_status)}
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-2">
                      {inv.summary_text || 'Active industrial heat anomaly dossier compiled for operational triage.'}
                    </p>

                    <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-100">
                      <div className="flex gap-4">
                        <span>Target: <strong>{inv.feature_id || 'Regional View'}</strong></span>
                        {inv.evidence_snapshot?.max_frp_mw != null && inv.evidence_snapshot.max_frp_mw > 0 ? (
                          <span>Max FRP: <strong className="text-amber-700">{inv.evidence_snapshot.max_frp_mw.toFixed(1)} MW</strong></span>
                        ) : (
                          <span>Max FRP: <strong className="text-slate-400 font-normal">Ground check required</strong></span>
                        )}
                        <span>Date: <strong>{inv.created_at ? new Date(inv.created_at).toLocaleDateString() : 'Active'}</strong></span>
                      </div>
                      <span className="text-indigo-600 font-semibold flex items-center gap-1">
                        Inspect Dossier &rarr;
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Dossier Inspector & Status Workflow */}
        <div className="space-y-4">
          {selectedInv ? (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 sticky top-20 text-xs">
              <div className="flex justify-between items-start pb-3 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Active Dossier</span>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">{selectedInv.report_key}</h3>
                  <div className="text-xs text-slate-500 mt-0.5">{selectedInv.region_name}</div>
                </div>
                {getStatusBadge(selectedInv.human_review_status)}
              </div>

              {/* Dossier Summary Box */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5">
                <div className="font-semibold text-slate-800 text-xs">{selectedInv.title}</div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  {selectedInv.summary_text}
                </p>

                {/* 5-Step Analyst Verification Protocol */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs font-mono">
                  <div className="text-[10px] font-bold text-slate-500 uppercase flex items-center justify-between">
                    <span>Analyst Verification Protocol</span>
                    <span className="text-emerald-700 font-bold">Standard 5-Step SOP</span>
                  </div>
                  <div className="space-y-1 text-[10.5px]">
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span>1. Spatial boundary check (&le; 500m to facility footprint)</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span>2. Multi-level baseline maturity review (N &ge; 30 mature)</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span>3. Multi-model consensus check (&ge; 2/3 models concur)</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span>4. Environmental flammability risk (high wind / dry fuel)</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span>5. Field dispatch & statutory compliance escalation</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Workflow State Transition Form */}
              <div className="p-3.5 bg-indigo-50/40 border border-indigo-200 rounded-xl space-y-3">
                <div className="flex items-center gap-1.5 font-bold font-mono text-indigo-900">
                  <UserCheck className="w-4 h-4 text-indigo-600" />
                  <span>Update Reviewer State Machine</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-700">Transition State To:</label>
                  <select
                    value={transitionStatus}
                    onChange={(e) => setTransitionStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white text-xs text-slate-800 font-semibold"
                  >
                    {validStates.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-700">Analyst / Field Review Notes:</label>
                  <textarea
                    rows={2}
                    value={reviewerNotes}
                    onChange={(e) => setReviewerNotes(e.target.value)}
                    placeholder="Document ground-truth observation, plant operator contact, or inspection dispatch notes..."
                    className="w-full p-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>

                <button
                  onClick={handleUpdateStatus}
                  disabled={transitioning}
                  className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-xs transition-colors"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{transitioning ? 'Saving State...' : 'Commit Status Transition'}</span>
                </button>

                {feedbackMsg && (
                  <div className="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-medium">
                    {feedbackMsg}
                  </div>
                )}
              </div>

              {/* Action Buttons: AI Investigator & Inspect on Map */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => setIsChatOpen(true)}
                  className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-xs transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Ask AI Investigator About This Dossier</span>
                </button>

                {onOpenReportModal && (
                  <button
                    onClick={() => onOpenReportModal('feature', selectedInv.feature_type, selectedInv.feature_id || '')}
                    className="w-full py-2 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-800 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
                  >
                    <FileText className="w-3.5 h-3.5 text-blue-600" />
                    <span>Download Evidence PDF & CSV Dossier</span>
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 border border-dashed border-slate-300 rounded-xl p-8 text-center text-slate-500 text-xs">
              Select any investigation dossier from the left to inspect its evidence and manage human verification status.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
