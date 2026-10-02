import React, { useEffect, useState } from 'react';
import {
  FileText,
  Download,
  Send,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Layers,
  Crosshair,
  Filter,
  Search,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Building2,
  FileSpreadsheet,
  History,
  Tag,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { Region, ReportScope } from '../types';

interface ReportsViewProps {
  selectedRegion: Region | null;
  onOpenReportModal: (scope: ReportScope, featureType?: string, featureId?: string) => void;
  selectedFeature?: { type: string; id: string; name?: string } | null;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  selectedRegion,
  onOpenReportModal,
  selectedFeature,
}) => {
  const [reports, setReports] = useState<any[]>([]);
  const [totalReports, setTotalReports] = useState(0);
  const [loading, setLoading] = useState(true);
  const [scopeFilter, setScopeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedReport, setSelectedReport] = useState<any | null>(null);

  // Authority Submission Modal State
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [authorities, setAuthorities] = useState<any[]>([]);
  const [selectedAuthId, setSelectedAuthId] = useState('');
  const [submissionChannel, setSubmissionChannel] = useState('PORTAL');
  const [submissionRefNum, setSubmissionRefNum] = useState('');
  const [submissionAckNum, setSubmissionAckNum] = useState('');
  const [submissionNotes, setSubmissionNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitFeedback, setSubmitFeedback] = useState<string | null>(null);

  // Review Status Transition State
  const [newStatus, setNewStatus] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    fetchReports();
    api.getAuthorities().then((res) => {
      setAuthorities(res.authorities || []);
      if (res.authorities && res.authorities.length > 0) {
        setSelectedAuthId(res.authorities[0].authority_id);
      }
    }).catch((err) => console.error('Failed to load authorities:', err));
  }, [selectedRegion]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      const res = await api.getReports({
        region: selectedRegion?.name,
        limit: 50,
      });
      setReports(res.reports || []);
      setTotalReports(res.total || 0);
      if (res.reports && res.reports.length > 0 && !selectedReport) {
        loadReportDetail(res.reports[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadReportDetail = async (id: number) => {
    try {
      const rep = await api.getReport(id);
      setSelectedReport(rep);
      setNewStatus(rep.status || 'generated');
      setReviewNotes('');
    } catch (err) {
      console.error('Failed to load report detail:', err);
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedReport || !newStatus) return;
    try {
      setUpdatingStatus(true);
      const res = await api.updateReportReviewStatus(selectedReport.id, newStatus, reviewNotes);
      setSelectedReport({
        ...selectedReport,
        status: res.status,
        approval_trail: res.approval_trail,
      });
      fetchReports();
    } catch (err) {
      console.error('Failed to transition status:', err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleRecordSubmission = async () => {
    if (!selectedReport || !selectedAuthId || !submissionRefNum) return;
    try {
      setSubmitting(true);
      setSubmitFeedback(null);
      await api.recordAuthoritySubmission({
        report_id: selectedReport.id,
        authority_id: selectedAuthId,
        channel: submissionChannel,
        reference_number: submissionRefNum,
        acknowledgement_number: submissionAckNum || undefined,
        notes: submissionNotes || undefined,
      });
      setSubmitFeedback('Submission successfully logged with official docket reference.');
      setTimeout(() => {
        setIsSubmitModalOpen(false);
        setSubmitFeedback(null);
        setSubmissionRefNum('');
        setSubmissionAckNum('');
        setSubmissionNotes('');
        loadReportDetail(selectedReport.id);
        fetchReports();
      }, 1500);
    } catch (err: any) {
      setSubmitFeedback(`Error: ${err.message || 'Submission failed'}`);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredReports = reports.filter((r) => {
    if (scopeFilter !== 'all' && r.scope !== scopeFilter) return false;
    if (statusFilter !== 'all' && (r.status || 'generated').toLowerCase() !== statusFilter.toLowerCase()) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        r.report_key.toLowerCase().includes(q) ||
        r.title.toLowerCase().includes(q) ||
        (r.region_name && r.region_name.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  const getStatusBadge = (status: string) => {
    const s = (status || 'generated').toUpperCase();
    switch (s) {
      case 'APPROVED':
        return <span className="badge bg-emerald-50 text-emerald-800 border-emerald-200">Approved</span>;
      case 'SUBMITTED':
        return <span className="badge bg-blue-50 text-blue-800 border-blue-200">Submitted</span>;
      case 'ACKNOWLEDGED':
        return <span className="badge bg-purple-50 text-purple-800 border-purple-200">Acknowledged</span>;
      case 'UNDER_REVIEW':
        return <span className="badge bg-amber-50 text-amber-800 border-amber-200">Under Review</span>;
      case 'CLOSED':
        return <span className="badge bg-slate-100 text-slate-700 border-slate-300">Closed</span>;
      default:
        return <span className="badge bg-indigo-50 text-indigo-700 border-indigo-200">Generated</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              Intelligence Reports & Statutory Document Generation
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Two-layer deterministic intelligence engine producing 15-part formal dossiers with ReportLab PDF and CSV evidence exports.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenReportModal('region')}
            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-2 shadow-xs transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>New Report Wizard</span>
          </button>
        </div>
      </div>

      {/* Scope Generator Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          onClick={() => onOpenReportModal('region')}
          className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-blue-500 hover:shadow-xs transition-all group space-y-2"
        >
          <div className="flex justify-between items-center">
            <span className="badge badge-gold font-mono text-[10px]">SCOPE 1</span>
            <FileText className="w-4 h-4 text-blue-600" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors uppercase font-mono">
            Regional Thermal Intelligence
          </h3>
          <p className="text-xs text-slate-500">
            Regional baseline FRP summary for {selectedRegion?.name || 'Pan-India Overview'} with persistent clusters and OSM facilities.
          </p>
          <div className="pt-2 text-[11px] text-blue-600 font-mono font-semibold group-hover:underline">
            Generate Region Dossier →
          </div>
        </div>

        <div
          onClick={() => onOpenReportModal('viewport')}
          className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-indigo-500 hover:shadow-xs transition-all group space-y-2"
        >
          <div className="flex justify-between items-center">
            <span className="badge bg-indigo-50 text-indigo-700 border-indigo-200 font-mono text-[10px]">SCOPE 2</span>
            <Layers className="w-4 h-4 text-indigo-600" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 group-hover:text-indigo-600 transition-colors uppercase font-mono">
            Map Viewport Extent
          </h3>
          <p className="text-xs text-slate-500">
            Spatial bounding-box query analyzing anomalies and infrastructure strictly inside current map coordinates.
          </p>
          <div className="pt-2 text-[11px] text-indigo-600 font-mono font-semibold group-hover:underline">
            Generate Viewport Dossier →
          </div>
        </div>

        <div
          onClick={() => {
            if (selectedFeature) {
              onOpenReportModal('feature', selectedFeature.type, selectedFeature.id);
            } else {
              onOpenReportModal('feature');
            }
          }}
          className="bg-white border border-slate-200 rounded-xl p-4 cursor-pointer hover:border-emerald-500 hover:shadow-xs transition-all group space-y-2"
        >
          <div className="flex justify-between items-center">
            <span className="badge bg-emerald-50 text-emerald-700 border-emerald-200 font-mono text-[10px]">SCOPE 3</span>
            <Crosshair className="w-4 h-4 text-emerald-600" />
          </div>
          <h3 className="text-xs font-bold text-slate-900 group-hover:text-emerald-600 transition-colors uppercase font-mono">
            Selected Target Feature
          </h3>
          <p className="text-xs text-slate-500">
            {selectedFeature
              ? `Strictly grounded analysis on target ${selectedFeature.name || selectedFeature.id}.`
              : 'Targeted single-cluster or observation analysis with baseline FRP and facility proximity.'}
          </p>
          <div className="pt-2 text-[11px] text-emerald-600 font-mono font-semibold group-hover:underline">
            {selectedFeature ? 'Analyze Target Feature →' : 'Select Target Feature →'}
          </div>
        </div>
      </div>

      {/* Main Archive & Inspection Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Report Archive List (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search report key, title, region..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <div className="flex items-center gap-2 text-xs">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={scopeFilter}
                onChange={(e) => setScopeFilter(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1.5 bg-white text-xs text-slate-700"
              >
                <option value="all">All Scopes</option>
                <option value="region">Region</option>
                <option value="viewport">Viewport</option>
                <option value="feature">Feature</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1.5 bg-white text-xs text-slate-700"
              >
                <option value="all">All Statuses</option>
                <option value="generated">Generated</option>
                <option value="under_review">Under Review</option>
                <option value="approved">Approved</option>
                <option value="submitted">Submitted</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-xl">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
              <div className="text-xs text-slate-500 font-mono">Loading report archive...</div>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-xl space-y-2">
              <FileText className="w-8 h-8 text-slate-300 mx-auto" />
              <div className="text-xs font-semibold text-slate-700">No reports found matching query</div>
              <div className="text-[11px] text-slate-500">Generate a new report using the wizard above.</div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredReports.map((r) => {
                const isSelected = selectedReport?.id === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => loadReportDetail(r.id)}
                    className={`bg-white border rounded-xl p-4 cursor-pointer transition-all shadow-xs ${
                      isSelected
                        ? 'border-blue-500 ring-2 ring-blue-100 bg-blue-50/20'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">{r.report_key}</span>
                        <span className="badge badge-gold font-mono text-[10px]">{r.scope.toUpperCase()}</span>
                        <span className="badge bg-slate-100 text-slate-600 font-mono text-[10px]">{r.version || 'v1.0'}</span>
                      </div>
                      {getStatusBadge(r.status)}
                    </div>

                    <h4 className="text-xs font-bold text-slate-800 line-clamp-1 mb-1">{r.title}</h4>
                    <p className="text-[11px] text-slate-500 line-clamp-2 mb-2 leading-relaxed">
                      {r.summary || 'Authoritative technical surveillance assessment compiled for environmental review.'}
                    </p>

                    <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 pt-2 border-t border-slate-100">
                      <span>Region: <strong className="text-slate-700">{r.region_name || 'Pan-India'}</strong></span>
                      <span>Date: <strong className="text-slate-700">{r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Recent'}</strong></span>
                      <span className="text-blue-600 font-semibold group-hover:underline">Inspect Dossier →</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Report Inspector (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          {selectedReport ? (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 sticky top-20 text-xs">
              <div className="flex justify-between items-start pb-3 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Intelligence Dossier</span>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">{selectedReport.report_key}</h3>
                  <div className="text-xs text-slate-500 mt-0.5">{selectedReport.region_name} · {selectedReport.version || 'v1.0'}</div>
                </div>
                {getStatusBadge(selectedReport.status)}
              </div>

              {/* Action Buttons: PDF, CSV, Submit */}
              <div className="grid grid-cols-3 gap-2">
                <a
                  href={api.getReportPdfUrl(selectedReport.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="py-2 px-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>PDF Report</span>
                </a>

                <a
                  href={api.getReportCsvUrl(selectedReport.id)}
                  download
                  className="py-2 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Evidence CSV</span>
                </a>

                <button
                  onClick={() => setIsSubmitModalOpen(true)}
                  className="py-2 px-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Submit SPCB</span>
                </button>
              </div>

              {/* Executive Summary */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5">
                <div className="font-semibold text-slate-800 text-xs">{selectedReport.title}</div>
                <p className="text-[11px] text-slate-600 leading-relaxed max-h-36 overflow-y-auto pr-1">
                  {selectedReport.summary || selectedReport.sections?.executive_summary}
                </p>
              </div>

              {/* Status Transition Machine */}
              <div className="p-3 bg-blue-50/40 border border-blue-200 rounded-xl space-y-2.5">
                <div className="flex items-center gap-1.5 font-bold font-mono text-blue-900 text-xs">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <span>8-Stage Approval Workflow</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-700">Transition Status To:</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded bg-white text-xs text-slate-800 font-semibold"
                  >
                    <option value="DRAFT">DRAFT (Analyst Work in Progress)</option>
                    <option value="GENERATED">GENERATED (Automated Calculations Complete)</option>
                    <option value="UNDER_REVIEW">UNDER_REVIEW (Supervisor Compliance Desk)</option>
                    <option value="APPROVED">APPROVED (Authorized for Authority Routing)</option>
                    <option value="SUBMITTED">SUBMITTED (Dispatched to Statutory Body)</option>
                    <option value="ACKNOWLEDGED">ACKNOWLEDGED (Official Inward Docket Received)</option>
                    <option value="RETURNED">RETURNED (Additional Evidence Requested)</option>
                    <option value="CLOSED">CLOSED (Verification Completed)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-700">Review Notes / Remarks:</label>
                  <textarea
                    rows={2}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Document endorsement remarks or legal compliance notes..."
                    className="w-full p-2 border border-slate-300 rounded text-xs"
                  />
                </div>

                <button
                  onClick={handleUpdateStatus}
                  disabled={updatingStatus}
                  className="w-full py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors shadow-xs"
                >
                  {updatingStatus ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  <span>Commit Status Transition</span>
                </button>
              </div>

              {/* Submissions History for this Report */}
              {selectedReport.submissions && selectedReport.submissions.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="text-[11px] font-bold text-slate-700 uppercase font-mono">
                    Statutory Submissions Log ({selectedReport.submissions.length})
                  </div>
                  <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
                    {selectedReport.submissions.map((sub: any) => (
                      <div key={sub.id} className="p-2 rounded bg-slate-50 border border-slate-200 text-[11px] space-y-0.5">
                        <div className="flex justify-between font-bold text-slate-800">
                          <span>{sub.authority_name}</span>
                          <span className="badge bg-purple-50 text-purple-700 text-[10px]">{sub.status}</span>
                        </div>
                        <div className="text-slate-500 font-mono text-[10px]">
                          Ref: {sub.reference_number} · {sub.channel}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-xl text-slate-400 font-mono text-xs">
              Select a report from the archive to inspect details.
            </div>
          )}
        </div>
      </div>

      {/* Authority Submission Modal */}
      {isSubmitModalOpen && selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-start pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-purple-600" />
                  <h3 className="text-sm font-bold text-slate-900 uppercase font-mono">
                    Official Statutory Authority Routing
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Record formal filing of report <strong className="text-slate-800 font-mono">{selectedReport.report_key}</strong>.
                </p>
              </div>
              <button
                onClick={() => setIsSubmitModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Target Authority:</label>
                <select
                  value={selectedAuthId}
                  onChange={(e) => setSelectedAuthId(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg bg-white text-xs font-semibold text-slate-800"
                >
                  {authorities.map((a) => (
                    <option key={a.authority_id} value={a.authority_id}>
                      {a.authority_name} ({a.jurisdiction})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">Delivery Channel:</label>
                  <select
                    value={submissionChannel}
                    onChange={(e) => setSubmissionChannel(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-lg bg-white text-xs"
                  >
                    <option value="PORTAL">Official Online Portal</option>
                    <option value="EMAIL">Secure Encrypted Email</option>
                    <option value="PHYSICAL_DISPATCH">Physical Speed Post / Docket</option>
                    <option value="API">Govt API Dispatch</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                    Filing Reference Number <span className="text-rose-500">*</span>:
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CPCB/AIR/2026/IND-9912"
                    value={submissionRefNum}
                    onChange={(e) => setSubmissionRefNum(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-lg text-xs font-mono font-semibold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Inward Docket / Acknowledgement ID (Optional):
                </label>
                <input
                  type="text"
                  placeholder="e.g. ACK-OD-2026-4412"
                  value={submissionAckNum}
                  onChange={(e) => setSubmissionAckNum(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">Officer Notes & Filing Remarks:</label>
                <textarea
                  rows={2}
                  value={submissionNotes}
                  onChange={(e) => setSubmissionNotes(e.target.value)}
                  placeholder="Document submission officer name, division, or expedited inspection requests..."
                  className="w-full p-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              {submitFeedback && (
                <div className={`p-2.5 rounded-lg text-xs font-semibold ${
                  submitFeedback.startsWith('Error') ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}>
                  {submitFeedback}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => setIsSubmitModalOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs text-slate-700 font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRecordSubmission}
                disabled={submitting || !submissionRefNum}
                className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50"
              >
                {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>Record Official Submission</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
