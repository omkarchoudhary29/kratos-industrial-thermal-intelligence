import React, { useState } from 'react';
import { BookmarkPlus, X, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { FollowUpPriority, FollowUpStatus } from '../types';
import { api } from '../services/api';

interface FollowUpModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialFeatureType?: string;
  initialFeatureId?: string;
  initialRegionName?: string;
  initialReportId?: number | null;
  onCreated?: () => void;
}

export const FollowUpModal: React.FC<FollowUpModalProps> = ({
  isOpen,
  onClose,
  initialFeatureType = 'cluster',
  initialFeatureId = '',
  initialRegionName = '',
  initialReportId = null,
  onCreated,
}) => {
  const [title, setTitle] = useState(
    initialFeatureId ? `Follow-up on ${initialFeatureType} ${initialFeatureId}` : 'Thermal Anomaly Investigation Task'
  );
  const [featureType, setFeatureType] = useState(initialFeatureType);
  const [featureId, setFeatureId] = useState(initialFeatureId);
  const [regionName, setRegionName] = useState(initialRegionName);
  const [priority, setPriority] = useState<FollowUpPriority>('HIGH');
  const [status, setStatus] = useState<FollowUpStatus>('OPEN');
  const [description, setDescription] = useState('');
  const [assignedTo, setAssignedTo] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !featureId.trim()) {
      setError('Title and Feature ID are required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.createFollowUp({
        title: title.trim(),
        feature_type: featureType,
        feature_id: featureId.trim(),
        region_name: regionName.trim() || 'General Corridor',
        report_id: initialReportId,
        priority,
        status,
        description: description.trim() || undefined,
        assigned_to: assignedTo.trim() || undefined,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      });

      if (onCreated) onCreated();
      onClose();
    } catch (err: any) {
      console.error('Failed to create follow-up task:', err);
      setError(err.message || 'Failed to submit follow-up task.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col text-slate-800">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <BookmarkPlus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase font-mono tracking-wide">
                Initiate Follow-up Task
              </h3>
              <span className="text-[11px] text-slate-500">
                Persistent Operational Tracking & Field Action Assignment
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center gap-2 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-slate-700 mb-1">
              Task Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Verify elevated blast furnace flare stack in Bokaro"
              className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Target Feature Type
              </label>
              <select
                value={featureType}
                onChange={(e) => setFeatureType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs font-mono"
              >
                <option value="cluster">Persistent Cluster</option>
                <option value="observation">Thermal Observation</option>
                <option value="facility">OSM Facility</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Feature ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={featureId}
                onChange={(e) => setFeatureId(e.target.value)}
                placeholder="e.g. dhanbad_bokaro_source_10"
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Region / Corridor
              </label>
              <input
                type="text"
                value={regionName}
                onChange={(e) => setRegionName(e.target.value)}
                placeholder="e.g. dhanbad_bokaro"
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Operational Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as FollowUpPriority)}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs font-semibold"
              >
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Initial Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as FollowUpStatus)}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs"
              >
                <option value="OPEN">OPEN</option>
                <option value="ASSIGNED">ASSIGNED</option>
                <option value="IN_PROGRESS">IN PROGRESS</option>
                <option value="AWAITING_VERIFICATION">AWAITING VERIF.</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Assignee (Analyst / Officer)
              </label>
              <input
                type="text"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                placeholder="e.g. S. Sen (Environmental Officer)"
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                Resolution Due Date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-700 mb-1">
              Instructions & Verification Notes
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detail necessary field action, stack telemetry checks, or ground inspection instructions..."
              className="w-full px-3 py-2 rounded-lg bg-white border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-500 text-xs leading-relaxed"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Creating Task...' : 'Create Follow-up Task'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
