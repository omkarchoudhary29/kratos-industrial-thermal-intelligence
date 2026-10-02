import React, { useState, useEffect } from 'react';
import {
  ClipboardCheck,
  Plus,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  MessageSquare,
  Send,
  X,
  MapPin,
  Calendar,
  UserCheck,
  Layers,
  FileText,
  AlertCircle,
  GitMerge,
} from 'lucide-react';
import { FollowUpTaskData, FollowUpStatus, FollowUpPriority } from '../types';
import { api } from '../services/api';

interface FollowUpsViewProps {
  onInspectFeature?: (featureType: string, featureId: string) => void;
  onOpenCreateModal?: () => void;
}

export const FollowUpsView: React.FC<FollowUpsViewProps> = ({
  onInspectFeature,
  onOpenCreateModal,
}) => {
  const [tasks, setTasks] = useState<FollowUpTaskData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<any | null>(null);
  const [activeQueueTab, setActiveQueueTab] = useState<'critical' | 'high' | 'assigned' | 'verification' | 'overdue' | 'resolved' | 'all'>('critical');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Assignee editing state
  const [isEditingAssignee, setIsEditingAssignee] = useState(false);
  const [assignedToInput, setAssignedToInput] = useState('');

  // Note addition state
  const [newNoteText, setNewNoteText] = useState('');
  const [noteStatusChange, setNoteStatusChange] = useState<FollowUpStatus | ''>('');
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);

  // Administrative Merge State
  const [duplicateGroup, setDuplicateGroup] = useState<{ featureId: string; taskIds: number[] } | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [mergeFeedback, setMergeFeedback] = useState<string | null>(null);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await api.listFollowUps({ limit: 100 });
      const fetchedTasks = res.tasks || [];
      setTasks(fetchedTasks);

      // Check for potential duplicate groups (same feature_id and active status)
      const activeTasks = fetchedTasks.filter((t: any) =>
        ['OPEN', 'ASSIGNED', 'IN_PROGRESS', 'AWAITING_VERIFICATION'].includes(t.status)
      );
      const featureMap: Record<string, number[]> = {};
      for (const t of activeTasks) {
        if (!featureMap[t.feature_id]) featureMap[t.feature_id] = [];
        featureMap[t.feature_id].push(t.id);
      }
      const dup = Object.entries(featureMap).find(([_, ids]) => ids.length > 1);
      if (dup) {
        setDuplicateGroup({ featureId: dup[0], taskIds: dup[1] });
      } else {
        setDuplicateGroup(null);
      }
    } catch (err) {
      console.error('Failed to load follow-up tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleSelectTask = async (task: FollowUpTaskData) => {
    try {
      const fullTask = await api.getFollowUp(task.task_key);
      setSelectedTask(fullTask);
    } catch (err) {
      setSelectedTask(task);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !newNoteText.trim()) return;

    setIsSubmittingNote(true);
    try {
      await api.addFollowUpNote(selectedTask.task_key, {
        note_text: newNoteText.trim(),
        status_change: noteStatusChange || undefined,
      });

      // Refresh task detail & list
      const updated = await api.getFollowUp(selectedTask.task_key);
      setSelectedTask(updated);
      setNewNoteText('');
      setNoteStatusChange('');
      fetchTasks();
    } catch (err) {
      console.error('Failed to add note:', err);
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleUpdateStatus = async (newStatus: FollowUpStatus) => {
    if (!selectedTask) return;
    try {
      await api.updateFollowUp(selectedTask.task_key, { status: newStatus });
      const updated = await api.getFollowUp(selectedTask.task_key);
      setSelectedTask(updated);
      fetchTasks();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleUpdateAssignee = async (newAssignee: string) => {
    if (!selectedTask) return;
    try {
      await api.updateFollowUp(selectedTask.task_key, { assigned_to: newAssignee.trim() });
      const updated = await api.getFollowUp(selectedTask.task_key);
      setSelectedTask(updated);
      setIsEditingAssignee(false);
      fetchTasks();
    } catch (err) {
      console.error('Failed to update assignee:', err);
    }
  };

  const handleMergeDuplicates = async () => {
    if (!duplicateGroup || duplicateGroup.taskIds.length < 2) return;
    try {
      setIsMerging(true);
      setMergeFeedback(null);
      const primaryId = duplicateGroup.taskIds[0];
      const secondaryIds = duplicateGroup.taskIds.slice(1);
      await api.mergeFollowUps(primaryId, secondaryIds, 'Administrative merge of correlated duplicate operational tasks.');
      setMergeFeedback(`Successfully merged ${secondaryIds.length} tasks into primary task #${primaryId}.`);
      setTimeout(() => {
        setMergeFeedback(null);
        fetchTasks();
      }, 2000);
    } catch (err: any) {
      setMergeFeedback(`Merge failed: ${err.message}`);
    } finally {
      setIsMerging(false);
    }
  };

  // 6 Sectioned Operational Queues
  const now = new Date();
  const criticalTasks = tasks.filter((t) => t.priority === 'CRITICAL' && t.status !== 'RESOLVED' && t.status !== 'CLOSED');
  const highPriorityTasks = tasks.filter((t) => t.priority === 'HIGH' && t.status !== 'RESOLVED' && t.status !== 'CLOSED');
  const assignedTasks = tasks.filter((t) => Boolean(t.assigned_to) && t.status !== 'RESOLVED' && t.status !== 'CLOSED');
  const awaitingVerifTasks = tasks.filter((t) => ['AWAITING_FIELD_VERIFICATION', 'AWAITING_VERIFICATION', 'UNDER_REVIEW'].includes(t.status));
  const overdueTasks = tasks.filter((t) => t.due_date && new Date(t.due_date) < now && t.status !== 'RESOLVED' && t.status !== 'CLOSED');
  const resolvedTasks = tasks.filter((t) => t.status === 'RESOLVED' || t.status === 'CLOSED');

  // Filter based on active queue tab and search query
  const getQueueTasks = () => {
    switch (activeQueueTab) {
      case 'critical':
        return criticalTasks;
      case 'high':
        return highPriorityTasks;
      case 'assigned':
        return assignedTasks;
      case 'verification':
        return awaitingVerifTasks;
      case 'overdue':
        return overdueTasks;
      case 'resolved':
        return resolvedTasks;
      default:
        return tasks;
    }
  };

  const displayedTasks = getQueueTasks().filter((t) => {
    if (statusFilter !== 'ALL' && t.status !== statusFilter) return false;
    if (priorityFilter !== 'ALL' && t.priority !== priorityFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.title.toLowerCase().includes(q) ||
      t.feature_id.toLowerCase().includes(q) ||
      t.task_key.toLowerCase().includes(q) ||
      t.region_name.toLowerCase().includes(q) ||
      (t.assigned_to && t.assigned_to.toLowerCase().includes(q))
    );
  });

  const getPriorityBadge = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'CRITICAL':
        return <span className="badge bg-red-50 text-red-700 border-red-200 font-bold">CRITICAL</span>;
      case 'HIGH':
        return <span className="badge bg-amber-50 text-amber-800 border-amber-200 font-bold">HIGH</span>;
      case 'MEDIUM':
        return <span className="badge bg-blue-50 text-blue-700 border-blue-200 font-bold">MEDIUM</span>;
      default:
        return <span className="badge bg-slate-100 text-slate-700 border-slate-200 font-bold">LOW</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'RESOLVED':
        return <span className="badge bg-emerald-50 text-emerald-800 border-emerald-200">RESOLVED</span>;
      case 'CLOSED':
        return <span className="badge bg-slate-100 text-slate-700 border-slate-300">CLOSED</span>;
      case 'UNDER_REVIEW':
        return <span className="badge bg-indigo-50 text-indigo-800 border-indigo-200">UNDER REVIEW</span>;
      case 'AWAITING_FIELD_VERIFICATION':
      case 'AWAITING_VERIFICATION':
        return <span className="badge bg-purple-50 text-purple-800 border-purple-200">AWAITING VERIF.</span>;
      case 'IN_PROGRESS':
        return <span className="badge bg-amber-50 text-amber-800 border-amber-200">IN PROGRESS</span>;
      case 'ASSIGNED':
        return <span className="badge bg-cyan-50 text-cyan-800 border-cyan-200">ASSIGNED</span>;
      default:
        return <span className="badge bg-blue-50 text-blue-800 border-blue-200">OPEN</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              High-Priority Follow-up & Verification Management
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational triage system for high and critical thermal anomalies, ground inspection dispatches, and immutable resolution audit trails.
          </p>
        </div>

        {onOpenCreateModal && (
          <button
            onClick={onOpenCreateModal}
            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-2 shadow-xs transition-colors font-mono"
          >
            <Plus className="w-4 h-4" />
            <span>New Follow-up Task</span>
          </button>
        )}
      </div>

      {/* Duplicate Prevention & Idempotency Alert */}
      {duplicateGroup && (
        <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <span className="font-bold text-amber-900 font-mono">Correlated Task Group Detected:</span>
              <p className="text-amber-800 mt-0.5">
                Target feature <strong className="font-mono">{duplicateGroup.featureId}</strong> has {duplicateGroup.taskIds.length} concurrent open tasks (#{duplicateGroup.taskIds.join(', #')}).
              </p>
            </div>
          </div>
          <button
            onClick={handleMergeDuplicates}
            disabled={isMerging}
            className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-xs shrink-0"
          >
            <GitMerge className="w-3.5 h-3.5" />
            <span>{isMerging ? 'Merging...' : 'Merge Duplicates'}</span>
          </button>
        </div>
      )}

      {mergeFeedback && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-blue-600" />
          <span>{mergeFeedback}</span>
        </div>
      )}

      {/* Sectioned Queue KPI Cards - 6 Dedicated Operational Queues */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <button
          onClick={() => setActiveQueueTab('critical')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'critical'
              ? 'bg-red-50/80 border-red-300 ring-2 ring-red-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-red-600 uppercase font-bold block">1. Critical Queue</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{criticalTasks.length}</span>
          <span className="text-[10px] text-slate-500">P ≥ 85 urgency</span>
        </button>

        <button
          onClick={() => setActiveQueueTab('high')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'high'
              ? 'bg-amber-50/80 border-amber-300 ring-2 ring-amber-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-amber-600 uppercase font-bold block">2. High-Priority</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{highPriorityTasks.length}</span>
          <span className="text-[10px] text-slate-500">70 ≤ P &lt; 85 triage</span>
        </button>

        <button
          onClick={() => setActiveQueueTab('assigned')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'assigned'
              ? 'bg-cyan-50/80 border-cyan-300 ring-2 ring-cyan-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-cyan-700 uppercase font-bold block">3. Assigned Tasks</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{assignedTasks.length}</span>
          <span className="text-[10px] text-slate-500">Delegated operators</span>
        </button>

        <button
          onClick={() => setActiveQueueTab('verification')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'verification'
              ? 'bg-purple-50/80 border-purple-300 ring-2 ring-purple-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-purple-600 uppercase font-bold block">4. Verification</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{awaitingVerifTasks.length}</span>
          <span className="text-[10px] text-slate-500">Field & under review</span>
        </button>

        <button
          onClick={() => setActiveQueueTab('overdue')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'overdue'
              ? 'bg-rose-50/80 border-rose-300 ring-2 ring-rose-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-rose-600 uppercase font-bold block">5. Overdue Tasks</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{overdueTasks.length}</span>
          <span className="text-[10px] text-slate-500">Exceeded SLA target</span>
        </button>

        <button
          onClick={() => setActiveQueueTab('resolved')}
          className={`p-3 rounded-xl border text-left transition-all ${activeQueueTab === 'resolved'
              ? 'bg-emerald-50/80 border-emerald-300 ring-2 ring-emerald-100 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
        >
          <span className="text-[10px] font-mono text-emerald-600 uppercase font-bold block">6. Resolved Archive</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-0.5 block">{resolvedTasks.length}</span>
          <span className="text-[10px] text-slate-500">Audited & closed</span>
        </button>
      </div>

      {/* Operational Priority Scale & Scientific Safeguard Card */}
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
        <div className="leading-relaxed">
          <strong className="text-slate-800">Operational Priority Standard:</strong> Priority scores ($0-100$) represent continuous operational triage urgency combining satellite radiative energy, persistence anomalies, and receptor proximity. <em>Operational priority is strictly an investigation dispatch indicator and must not be interpreted as physical fire or explosion probability without independent ground-truth confirmation.</em>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, feature ID, task key, or assignee..."
            className="w-full bg-transparent border-none text-xs text-slate-800 placeholder-slate-400 focus:outline-none font-mono"
          />
        </div>

        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-semibold">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-2 py-1.5 rounded border border-slate-300 bg-white text-slate-700 text-xs focus:outline-none"
            >
              <option value="ALL">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 font-semibold">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2 py-1.5 rounded border border-slate-300 bg-white text-slate-700 text-xs focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="AWAITING_VERIFICATION">Awaiting Verif.</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          <button
            onClick={fetchTasks}
            className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
            title="Refresh tasks"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Tasks Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        {loading ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
            Loading follow-up surveillance tasks...
          </div>
        ) : displayedTasks.length === 0 ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs space-y-2">
            <ClipboardCheck className="w-8 h-8 mx-auto text-slate-300" />
            <p className="font-semibold text-slate-700">No follow-up tasks match the active queue filter.</p>
            {onOpenCreateModal && (
              <button
                onClick={onOpenCreateModal}
                className="text-blue-600 hover:underline inline-block mt-1 font-semibold"
              >
                Create a new follow-up task →
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-slate-50/80 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4 font-bold">Task Key</th>
                  <th className="py-3 px-4 font-bold">Investigation Objective</th>
                  <th className="py-3 px-4 font-bold">Linked Feature</th>
                  <th className="py-3 px-4 font-bold">Region</th>
                  <th className="py-3 px-4 font-bold">Priority</th>
                  <th className="py-3 px-4 font-bold">Status</th>
                  <th className="py-3 px-4 font-bold">Assignee / Notes</th>
                  <th className="py-3 px-4 text-right font-bold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {displayedTasks.map((t) => {
                  return (
                    <tr
                      key={t.id}
                      onClick={() => handleSelectTask(t)}
                      className="hover:bg-blue-50/20 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-bold text-slate-900">{t.task_key}</td>
                      <td className="py-3 px-4 text-slate-800 font-sans font-medium max-w-[240px] truncate">
                        {t.title}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        <span className="uppercase text-[10px] text-slate-400 mr-1">
                          {t.feature_type}:
                        </span>
                        <span className="text-slate-900 font-semibold">{t.feature_id}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-600">{t.region_name}</td>
                      <td className="py-3 px-4">{getPriorityBadge(t.priority)}</td>
                      <td className="py-3 px-4">{getStatusBadge(t.status)}</td>
                      <td className="py-3 px-4 text-[11px] text-slate-600">
                        <div className="font-semibold text-slate-800">{t.assigned_to || t.created_by_name || 'Unassigned'}</div>
                        <div className="text-[10px] text-slate-400">{t.note_count || 0} audit notes</div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectTask(t);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 text-[11px] font-semibold transition-colors shadow-xs"
                        >
                          Manage →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Task Detail Slide-Over / Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-xl h-full bg-white border-l border-slate-200 shadow-2xl flex flex-col justify-between overflow-hidden text-slate-800">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-100 bg-slate-50/80 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-slate-900">{selectedTask.task_key}</span>
                  {getStatusBadge(selectedTask.status)}
                  {getPriorityBadge(selectedTask.priority)}
                </div>
                <h3 className="text-sm font-bold text-slate-900 mt-1 font-sans">{selectedTask.title}</h3>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
              {/* Linked Feature & Action */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-mono block font-bold">Linked Target Feature</span>
                  <div className="font-mono text-xs font-bold text-slate-900 flex items-center gap-1.5 mt-0.5">
                    <MapPin className="w-3.5 h-3.5 text-blue-600" />
                    <span>[{selectedTask.feature_type.toUpperCase()}] {selectedTask.feature_id}</span>
                  </div>
                  <span className="text-[11px] text-slate-500">{selectedTask.region_name}</span>
                </div>

                {onInspectFeature && (
                  <button
                    onClick={() => {
                      onInspectFeature(selectedTask.feature_type, selectedTask.feature_id);
                      setSelectedTask(null);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-mono text-[11px] font-semibold flex items-center gap-1.5 transition-colors shadow-xs"
                  >
                    <span>Inspect on Map</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Status Update Quick Bar */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono uppercase font-bold text-slate-500">Update Task Status</label>
                <div className="grid grid-cols-5 gap-1.5">
                  <button
                    onClick={() => handleUpdateStatus('IN_PROGRESS')}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-mono border transition-colors ${selectedTask.status === 'IN_PROGRESS'
                        ? 'bg-amber-100 border-amber-300 text-amber-900 font-bold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    In Progress
                  </button>
                  <button
                    onClick={() => handleUpdateStatus('AWAITING_FIELD_VERIFICATION')}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-mono border transition-colors ${selectedTask.status === 'AWAITING_FIELD_VERIFICATION' || selectedTask.status === 'AWAITING_VERIFICATION'
                        ? 'bg-purple-100 border-purple-300 text-purple-900 font-bold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    Awaiting Verif.
                  </button>
                  <button
                    onClick={() => handleUpdateStatus('UNDER_REVIEW')}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-mono border transition-colors ${selectedTask.status === 'UNDER_REVIEW'
                        ? 'bg-indigo-100 border-indigo-300 text-indigo-900 font-bold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    Under Review
                  </button>
                  <button
                    onClick={() => handleUpdateStatus('RESOLVED')}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-mono border transition-colors ${selectedTask.status === 'RESOLVED'
                        ? 'bg-emerald-100 border-emerald-300 text-emerald-900 font-bold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    Resolved
                  </button>
                  <button
                    onClick={() => handleUpdateStatus('CLOSED')}
                    className={`py-1.5 px-2 rounded-lg text-[10px] font-mono border transition-colors ${selectedTask.status === 'CLOSED'
                        ? 'bg-slate-200 border-slate-400 text-slate-900 font-bold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                  >
                    Close
                  </button>
                </div>
              </div>

              {/* Assignment & Due Date */}
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-600">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 font-bold uppercase block">Responsible Assignee</span>
                    {!isEditingAssignee && (
                      <button
                        onClick={() => {
                          setAssignedToInput(selectedTask.assigned_to || '');
                          setIsEditingAssignee(true);
                        }}
                        className="text-[10px] font-mono text-blue-600 hover:text-blue-800 underline font-semibold"
                      >
                        Reassign
                      </button>
                    )}
                  </div>
                  {isEditingAssignee ? (
                    <div className="mt-1 space-y-1.5">
                      <input
                        type="text"
                        value={assignedToInput}
                        onChange={(e) => setAssignedToInput(e.target.value)}
                        placeholder="e.g. Lead Analyst, Inspector Raj"
                        className="w-full text-xs px-2 py-1 rounded border border-slate-300 bg-white focus:outline-blue-500 font-sans"
                        autoFocus
                      />
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => handleUpdateAssignee(assignedToInput)}
                          className="px-2 py-0.5 rounded bg-blue-600 text-white text-[10px] font-mono font-bold hover:bg-blue-700"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setIsEditingAssignee(false)}
                          className="px-2 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px] font-mono hover:bg-slate-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs font-semibold text-slate-800 block mt-0.5">
                      {selectedTask.assigned_to || 'Unassigned (General Pool)'}
                    </span>
                  )}
                </div>
                <div>
                  <span className="text-[10px] font-mono text-slate-400 font-bold uppercase block">Due Date</span>
                  <span className="text-xs font-semibold text-slate-800 block mt-0.5">
                    {selectedTask.due_date ? new Date(selectedTask.due_date).toLocaleDateString() : 'No deadline configured'}
                  </span>
                </div>
              </div>

              {/* Description */}
              {selectedTask.description && (
                <div className="space-y-1">
                  <span className="text-[11px] font-mono uppercase font-bold text-slate-500">Investigation Instructions</span>
                  <p className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 leading-relaxed">
                    {selectedTask.description}
                  </p>
                </div>
              )}

              {/* Audit Timeline / Notes */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <h4 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wider">
                  Audit History & Field Notes ({selectedTask.notes?.length || 0})
                </h4>

                <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
                  {selectedTask.notes && selectedTask.notes.length > 0 ? (
                    selectedTask.notes.map((note: any) => (
                      <div key={note.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                        <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
                          <span className="font-semibold text-slate-700">{note.author_name}</span>
                          <span>{note.created_at ? new Date(note.created_at).toLocaleString() : ''}</span>
                        </div>
                        <p className="text-[11px] text-slate-700 leading-relaxed">{note.note_text}</p>
                        {note.status_change && (
                          <span className="inline-block mt-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                            Status changed to: {note.status_change}
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-400 font-mono">No notes recorded yet.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Note Input Footer */}
            <form onSubmit={handleAddNote} className="p-4 border-t border-slate-100 bg-slate-50/80 space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newNoteText}
                  onChange={(e) => setNewNoteText(e.target.value)}
                  placeholder="Record operational ground-truth note or inspection finding..."
                  className="flex-1 px-3 py-2 rounded-lg bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={isSubmittingNote || !newNoteText.trim()}
                  className="px-3.5 py-2 rounded-lg bg-blue-600 text-white font-semibold text-xs flex items-center gap-1.5 hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-xs"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Log</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
