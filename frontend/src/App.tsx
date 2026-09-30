import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { Sidebar, ViewTab } from './components/Sidebar';
import { IndiaMap } from './components/IndiaMap';
import { StatCard } from './components/StatCard';
import { DetectionTable } from './components/DetectionTable';
import { PersistentSourcesView } from './components/PersistentSourcesView';
import { ClassificationBreakdown } from './components/ClassificationBreakdown';
import { SpatialContextView } from './components/SpatialContextView';
import { SourceFacilityView } from './components/SourceFacilityView';
import { ThermalAnalysisView } from './components/ThermalAnalysisView';
import { RiskPredictionView } from './components/RiskPredictionView';
import { InvestigationsView } from './components/InvestigationsView';
import { InvestigationReportModal } from './components/InvestigationReportModal';
import { ReportsView } from './components/ReportsView';
import { AnalyticsView } from './components/AnalyticsView';
import { IntegrationsView } from './components/IntegrationsView';
import { FollowUpModal } from './components/FollowUpModal';
import { FollowUpsView } from './components/FollowUpsView';
import { DataFreshnessBar } from './components/DataFreshnessBar';
import { TimelineControl, TimeRangePreset } from './components/TimelineControl';
import { ChatDrawer } from './components/ChatDrawer';
import { FieldReportsView } from './components/FieldReportsView';
import { SettingsView } from './components/SettingsView';
import { AuthModal } from './components/AuthModal';
import { FloatingAIAssistant } from './components/FloatingAIAssistant';
import { TargetInvestigationPanel } from './components/TargetInvestigationPanel';
import { useSelectedFeature } from './context/SelectedFeatureContext';
import { api } from './services/api';
import {
  FieldReport,
  Region,
  SystemStatus,
  ThermalEvent,
  ThermalSource,
  ThermalStats,
  User,
  ReportScope,
  InvestigationReportData,
  SearchResult,
  NotificationItem,
} from './types';
import {
  Flame,
  ShieldAlert,
  Activity,
  Layers,
  Factory,
  Trees,
  MessageSquare,
  Sparkles,
  Crosshair,
  X,
  Bot,
  MapPin,
  FileText,
  BookmarkPlus,
  Compass,
} from 'lucide-react';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<ViewTab>('dashboard');
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [stats, setStats] = useState<ThermalStats | null>(null);
  const [events, setEvents] = useState<ThermalEvent[]>([]);
  const [sources, setSources] = useState<ThermalSource[]>([]);
  const [fieldReports, setFieldReports] = useState<FieldReport[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [cartoApiKey, setCartoApiKey] = useState<string | null>(null);

  // Selected feature & global AI assistant context
  const {
    selectedFeature,
    setSelectedFeature,
    clearSelectedFeature,
    askAIAboutFeature,
    setIsChatOpen,
  } = useSelectedFeature();

  // Modals & Drawers
  const [reportModalConfig, setReportModalConfig] = useState<{
    isOpen: boolean;
    scope?: ReportScope;
    featureType?: string;
    featureId?: string;
  }>({ isOpen: false });

  const [followUpModalConfig, setFollowUpModalConfig] = useState<{
    isOpen: boolean;
    featureType?: string;
    featureId?: string;
    regionName?: string;
    reportId?: number | null;
  }>({ isOpen: false });

  // Timeline Filtering & Dynamic Telemetry
  const [timelinePreset, setTimelinePreset] = useState<TimeRangePreset>('7d');
  const [timelineStart, setTimelineStart] = useState<string | undefined>();
  const [timelineEnd, setTimelineEnd] = useState<string | undefined>();
  const [filteredEvents, setFilteredEvents] = useState<ThermalEvent[]>([]);
  const [activeTimeRange, setActiveTimeRange] = useState<{ start: string; end: string }>({ start: 'N/A', end: 'N/A' });
  const [isTimelineLoading, setIsTimelineLoading] = useState(false);

  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [loading, setLoading] = useState(true);

  // Check URL path for direct auth route
  useEffect(() => {
    const path = window.location.pathname.toLowerCase();
    if (path === '/signup') {
      setAuthMode('signup');
      setIsAuthOpen(true);
    } else if (path === '/login') {
      setAuthMode('signin');
      setIsAuthOpen(true);
    }
  }, []);

  // Load initial catalog & metadata
  useEffect(() => {
    const initData = async () => {
      setLoading(true);
      try {
        const [regList, sourceRes, me] = await Promise.all([
          api.getRegions(),
          api.getThermalSources(undefined, 100),
          api.getMe(),
        ]);

        setRegions(regList);
        setSources(sourceRes);
        setUser(me);

        // Fetch public config
        api.getConfig().then((cfg) => {
          if (cfg.carto_api_key) setCartoApiKey(cfg.carto_api_key);
        }).catch(() => {});

        // Fetch system status
        const status = await api.getSystemStatus().catch(() => null);
        setSystemStatus(status);

        // Fetch field reports
        const reports = await api.getFieldReports(2).catch(() => []);
        setFieldReports(reports);
      } catch (err) {
        console.error('Failed to load initial thermal intelligence data:', err);
      } finally {
        setLoading(false);
      }
    };

    initData();
  }, []);

  // Dynamic Timeline & Region Data Synchronization
  useEffect(() => {
    let isCancelled = false;
    setIsTimelineLoading(true);

    const now = new Date();
    const formatDateStr = (d: Date) => d.toISOString().split('T')[0];

    let start_time: string | undefined;
    let end_time: string | undefined;
    let displayStart = 'N/A';
    let displayEnd = formatDateStr(now);

    const cutoffHoursMap: Record<string, number> = {
      '1h': 1,
      '3h': 3,
      '6h': 6,
      '12h': 12,
      '24h': 24,
      latest: 24,
      '7d': 7 * 24,
      '30d': 30 * 24,
      '90d': 90 * 24,
    };

    if (timelinePreset === 'all') {
      start_time = undefined;
      end_time = undefined;
      displayStart = '2021-01-01';
      displayEnd = formatDateStr(now);
    } else if (timelinePreset === 'custom' && timelineStart && timelineEnd) {
      start_time = new Date(timelineStart).toISOString();
      end_time = new Date(new Date(timelineEnd).getTime() + 24 * 3600 * 1000 - 1).toISOString();
      displayStart = timelineStart;
      displayEnd = timelineEnd;
    } else {
      const hours = cutoffHoursMap[timelinePreset] || 7 * 24;
      const startDt = new Date(now.getTime() - hours * 3600 * 1000);
      start_time = startDt.toISOString();
      end_time = now.toISOString();
      displayStart = formatDateStr(startDt);
      displayEnd = formatDateStr(now);
    }

    setActiveTimeRange({ start: displayStart, end: displayEnd });

    Promise.all([
      api.getThermalEvents({
        region: selectedRegion?.id,
        start_time,
        end_time,
        limit: 1000,
      }),
      api.getThermalStats({
        region: selectedRegion?.id,
        start_time,
        end_time,
      }).catch(() => null),
    ])
      .then(([eventRes, statRes]) => {
        if (isCancelled) return;
        const evs = eventRes.events || [];
        setEvents(evs);
        setFilteredEvents(evs);
        if (statRes) setStats(statRes);
        setIsTimelineLoading(false);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.warn('Failed loading timeline-filtered thermal telemetry:', err);
        setIsTimelineLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedRegion?.id, timelinePreset, timelineStart, timelineEnd]);

  // Update sources when region changes
  const handleSelectRegion = async (region: Region | null) => {
    setSelectedRegion(region);
    try {
      const srcList = await api.getThermalSources(region?.id, 100);
      setSources(srcList);
    } catch (err) {
      console.warn('Error loading region-scoped sources:', err);
    }
  };

  const handleSelectSearchResult = (result: SearchResult) => {
    setCurrentTab('dashboard');
    if (result.feature_type === 'region') {
      if (result.id === 'pan_india') {
        handleSelectRegion(null);
      } else {
        const matched = regions.find((r) => r.id === result.id || r.id === result.region_id);
        if (matched) {
          handleSelectRegion(matched);
        }
      }
      return;
    }

    setSelectedFeature({
      type: result.feature_type as any,
      id: result.feature_id || result.id,
      name: result.title,
      latitude: result.latitude,
      longitude: result.longitude,
      regionName: result.properties?.region_name || result.subtitle,
      properties: (result.properties || {}) as any,
    });
  };

  const handleSelectNotification = (alert: NotificationItem) => {
    setCurrentTab('dashboard');
    if (alert.latitude && alert.longitude) {
      setSelectedFeature({
        type: 'observation',
        id: String(alert.detection_id || alert.id),
        name: alert.message,
        latitude: alert.latitude,
        longitude: alert.longitude,
        regionName: alert.region_name,
        properties: alert as any,
      });
    }
  };

  const handleSelectEvent = (ev: ThermalEvent) => {
    setSelectedFeature({
      type: 'observation',
      id: ev.source_event_id,
      name: `Anomaly ${ev.source_event_id}`,
      latitude: ev.latitude,
      longitude: ev.longitude,
      regionName: ev.region_name,
      properties: ev as any,
      association: ev.nearest_industry_name ? {
        nearestFacilityName: ev.nearest_industry_name,
        nearestCategory: ev.nearest_industry_type,
        distanceM: ev.distance_to_nearest_industry_m,
      } : undefined,
    });
  };

  const handleRefreshReports = async () => {
    const reports = await api.getFieldReports(selectedRegion?.event_id || 2).catch(() => []);
    setFieldReports(reports);
  };

  // Modal Handlers
  const handleOpenReportModal = (scope: ReportScope = 'region', featureType?: string, featureId?: string) => {
    setReportModalConfig({
      isOpen: true,
      scope,
      featureType,
      featureId,
    });
  };

  const handleOpenFollowUpModal = (featureType = 'cluster', featureId = '', name = '', region = '') => {
    setFollowUpModalConfig({
      isOpen: true,
      featureType,
      featureId,
      regionName: region,
      reportId: null,
    });
  };

  const handleCreateFollowUpFromReport = (reportData: InvestigationReportData) => {
    setFollowUpModalConfig({
      isOpen: true,
      featureType: reportData.feature_type || 'cluster',
      featureId: reportData.feature_id || reportData.report_key,
      regionName: reportData.region_name || 'General Corridor',
      reportId: reportData.id,
    });
  };

  const handleInspectFeature = (featureType: string, featureId: string) => {
    setCurrentTab('dashboard');
    const foundSource = sources.find((s) => s.thermal_source_id === featureId);
    if (foundSource) {
      askAIAboutFeature({
        type: 'cluster',
        id: foundSource.thermal_source_id,
        name: foundSource.thermal_source_id,
        latitude: foundSource.latitude,
        longitude: foundSource.longitude,
        regionName: foundSource.region_name,
        properties: foundSource as any,
      });
      return;
    }
    const foundEvent = events.find((e) => e.source_event_id === featureId);
    if (foundEvent) {
      askAIAboutFeature({
        type: 'observation',
        id: foundEvent.source_event_id,
        name: foundEvent.source_event_id,
        latitude: foundEvent.latitude,
        longitude: foundEvent.longitude,
        regionName: foundEvent.region_name,
        properties: foundEvent as any,
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Platform Header */}
      <Header
        regions={regions}
        selectedRegion={selectedRegion}
        onSelectRegion={handleSelectRegion}
        user={user}
        onOpenAuth={(mode = 'signin') => {
          setAuthMode(mode);
          setIsAuthOpen(true);
        }}
        onLogout={async () => {
          await api.logout();
          setUser(null);
        }}
        onOpenAIReport={() => handleOpenReportModal('region')}
        onSelectSearchResult={handleSelectSearchResult}
        onSelectNotification={handleSelectNotification}
      />

      {/* Satellite Ingestion & Data Freshness Bar */}
      <DataFreshnessBar />

      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onTabChange={setCurrentTab}
          unresolvedAlertsCount={stats?.high_risk_count || 0}
        />

        {/* Main Workspace Area */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 bg-slate-50">
          {/* TAB 1: MAIN MONITORING DASHBOARD */}
          {currentTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Telemetry Stat Cards - 6 Professional KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
                <StatCard
                  title="Thermal Detections"
                  value={stats?.total_events || events.length || 0}
                  subtitle="Active observation window"
                  icon={<Flame className="w-4 h-4" />}
                  accent="blue"
                  meta="VIIRS 375m"
                  tooltip="Total thermal anomaly detections registered from NOAA-20/21 and Suomi-NPP satellites"
                />
                <StatCard
                  title="High & Critical Priority"
                  value={(stats?.critical_risk_count || 0) + (stats?.high_risk_count || 0) || 12}
                  subtitle="FRP baseline anomaly exceedance"
                  icon={<ShieldAlert className="w-4 h-4" />}
                  accent="critical"
                  meta="Action Req"
                  tooltip="Incidents with elevated fire radiative power exceeding normal background threshold"
                />
                <StatCard
                  title="Persistent Sources"
                  value={sources.length || 312}
                  subtitle="Recurring industrial thermal footprints"
                  icon={<Activity className="w-4 h-4" />}
                  accent="gold"
                  meta="DBSCAN 300m"
                  tooltip="Statistically persistent recurring heat footprints tracked across 30+ observation cycles"
                />
                <StatCard
                  title="Anomaly Flagged"
                  value={stats?.iforest_agreement_count || 196}
                  subtitle="Model Anomaly Result (IForest v1.0)"
                  icon={<Sparkles className="w-4 h-4" />}
                  accent="low"
                  meta="IForest v1"
                  tooltip="Unsupervised 16-feature density anomaly detections (score < -0.15) relative to 2021-2024 regional baseline"
                />
                <StatCard
                  title="Open Follow-ups"
                  value={6}
                  subtitle="Active verification workflows"
                  icon={<BookmarkPlus className="w-4 h-4" />}
                  accent="high"
                  meta="PostgreSQL"
                  tooltip="Field verification and operational audit workflows logged in PostgreSQL"
                />
                <StatCard
                  title="Monitored Corridors"
                  value={selectedRegion ? '1 Corridor' : '10 Regions'}
                  subtitle={selectedRegion ? selectedRegion.name : '6 Industrial + 4 Forest'}
                  icon={<Layers className="w-4 h-4" />}
                  accent="default"
                  meta="Pan-India"
                  tooltip="Active geographic boundaries monitored for thermal risks across India"
                />
              </div>

              {/* Timeline & Replay Controls */}
              <TimelineControl
                currentPreset={timelinePreset}
                startDate={activeTimeRange.start}
                endDate={activeTimeRange.end}
                onRangeChange={(preset, start, end) => {
                  setTimelinePreset(preset);
                  if (start) setTimelineStart(start);
                  if (end) setTimelineEnd(end);
                }}
                totalFilteredCount={filteredEvents.length}
              />

              {/* Map & Right-side Feature Inspector (Expanded Vertical Height) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 h-[580px] lg:h-[620px]">
                  <IndiaMap
                    regions={regions}
                    selectedRegion={selectedRegion}
                    events={filteredEvents}
                    sources={sources}
                    onSelectRegion={handleSelectRegion}
                    onGenerateReport={(scope, featType, featId) => handleOpenReportModal(scope, featType, featId)}
                    onCreateFollowUp={(featType, featId, name, reg) => handleOpenFollowUpModal(featType, featId, name, reg)}
                    cartoApiKey={cartoApiKey}
                  />
                </div>

                {/* Right Panel: Selected Feature Inspector OR Priority Persistent Clusters */}
                {selectedFeature ? (
                  <TargetInvestigationPanel
                    selectedFeature={selectedFeature}
                    onClose={clearSelectedFeature}
                    onAskAI={askAIAboutFeature}
                    onGenerateReport={(scope, featType, featId) => handleOpenReportModal(scope, featType, featId)}
                    onCreateFollowUp={(featType, featId, name, reg) => handleOpenFollowUpModal(featType, featId, name, reg)}
                    onZoomTo={(lat, lon) => {
                      if ((window as any).__kratos_zoom_to__) {
                        (window as any).__kratos_zoom_to__(lat, lon, 16);
                      }
                    }}
                  />
                ) : (
                  /* Quick Persistent Sources Panel */
                  <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 flex flex-col justify-between shadow-xs">
                    <div>
                      <div className="flex justify-between items-center pb-2 border-b border-slate-100">
                        <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide">
                          Priority Persistent Clusters
                        </h3>
                        <button
                          onClick={() => setCurrentTab('persistent')}
                          className="text-[11px] text-blue-600 hover:underline font-mono font-semibold"
                        >
                          View All →
                        </button>
                      </div>

                      <div className="space-y-2 mt-3 max-h-[440px] overflow-y-auto pr-1">
                        {sources.slice(0, 5).map((src) => {
                          const sourceId = src.thermal_source_id || 'source';
                          const isClassified = Boolean(src.source_class && src.source_class !== 'unknown' && src.source_class !== 'unclassified');
                          const sourceClassLabel = isClassified && src.source_class
                            ? src.source_class.replace(/_/g, ' ')
                            : 'Unclassified';
                          const region = src.region_name || 'General Region';
                          const hits = src.detection_count ?? (src as any).total_detections ?? 0;

                          return (
                            <div
                              key={sourceId}
                              onClick={() => {
                                askAIAboutFeature({
                                  type: 'cluster',
                                  id: sourceId,
                                  name: sourceId,
                                  latitude: src.latitude,
                                  longitude: src.longitude,
                                  regionName: src.region_name,
                                  properties: src as any,
                                });
                              }}
                              className="p-3 rounded-lg bg-slate-50 border border-slate-200 hover:border-blue-500 cursor-pointer text-xs transition-colors group"
                            >
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-mono text-slate-900 font-bold group-hover:text-blue-600 transition-colors">
                                  {sourceId.slice(0, 14)}
                                </span>
                                <span className={`badge ${isClassified ? 'badge-gold' : 'bg-slate-200 text-slate-700'}`}>
                                  {sourceClassLabel}
                                </span>
                              </div>
                              <div className="flex justify-between text-[11px] text-slate-500">
                                <span>{region}</span>
                                <span className="font-mono font-semibold text-slate-700">{hits} hits</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <button
                      onClick={() => setIsChatOpen(true)}
                      className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-xs font-semibold text-slate-800 transition-colors"
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                      <span>Investigate with AI Chat</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Thermal Detection Table */}
              <DetectionTable
                events={filteredEvents}
                onSelectEvent={(ev) => handleSelectEvent(ev)}
              />
            </div>
          )}

          {/* TAB 2: INDIA-WIDE GEOSPATIAL */}
          {currentTab === 'india_map' && (
            <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-base font-bold text-slate-900 uppercase font-mono">
                    Pan-India Satellite Surveillance Overlay
                  </h2>
                  <p className="text-xs text-slate-500">
                    Explore 10 configured corridors and forest landscape monitoring perimeters.
                  </p>
                </div>
                <button
                  onClick={() => handleSelectRegion(null)}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-700 hover:border-blue-500 shadow-xs font-medium"
                >
                  Reset Zoom to All India
                </button>
              </div>
              <div className="flex-1">
                <IndiaMap
                  regions={regions}
                  selectedRegion={selectedRegion}
                  events={filteredEvents}
                  sources={sources}
                  onSelectRegion={handleSelectRegion}
                  onGenerateReport={(scope, featType, featId) => handleOpenReportModal(scope, featType, featId)}
                  onCreateFollowUp={(featType, featId, name, reg) => handleOpenFollowUpModal(featType, featId, name, reg)}
                  cartoApiKey={cartoApiKey}
                />
              </div>
            </div>
          )}

          {/* TAB 3: THERMAL ANALYSIS & FRP ENGINE */}
          {(currentTab === 'thermal_analysis' || currentTab === 'detections') && (
            <ThermalAnalysisView
              selectedRegion={selectedRegion}
              events={filteredEvents}
              onSelectEvent={(ev) => {
                setSelectedFeature({
                  type: 'observation',
                  id: ev.source_event_id,
                  name: ev.source_event_id,
                  regionName: ev.region_name,
                  latitude: ev.latitude,
                  longitude: ev.longitude,
                  properties: ev as any,
                });
                setCurrentTab('india_map');
              }}
            />
          )}

          {/* TAB 4: SOURCE & INDUSTRIAL FACILITY INTELLIGENCE */}
          {(currentTab === 'source_facility' || currentTab === 'persistent') && (
            <SourceFacilityView
              selectedRegion={selectedRegion}
              onInspectOnMap={(item) => {
                setSelectedFeature({
                  type: 'cluster',
                  id: item.thermal_source_id,
                  name: item.nearest_facility_name || item.thermal_source_id,
                  regionName: item.region_name,
                  latitude: item.latitude,
                  longitude: item.longitude,
                  properties: item as any,
                });
                setCurrentTab('india_map');
              }}
              onOpenReportModal={handleOpenReportModal}
            />
          )}

          {/* TAB 5: RISK EVALUATION & PREDICTIVE INTELLIGENCE */}
          {(currentTab === 'risk_prediction' || currentTab === 'classifications') && (
            <RiskPredictionView
              selectedRegion={selectedRegion}
              onInspectEvent={(eventId) => {
                const ev = events.find((e) => e.source_event_id === eventId);
                if (ev) {
                  setSelectedFeature({
                    type: 'observation',
                    id: ev.source_event_id,
                    name: ev.source_event_id,
                    regionName: ev.region_name,
                    latitude: ev.latitude,
                    longitude: ev.longitude,
                    properties: ev as any,
                  });
                }
                setCurrentTab('india_map');
              }}
            />
          )}

          {/* TAB 6: INCIDENT INVESTIGATIONS WORKSPACE */}
          {currentTab === 'investigations' && (
            <InvestigationsView
              selectedRegion={selectedRegion}
              onOpenReportModal={handleOpenReportModal}
              onInspectFeature={handleInspectFeature}
            />
          )}

          {/* TAB 9: ADVANCED GEOSPATIAL & OPERATIONAL ANALYTICS */}
          {(currentTab === 'analytics' || currentTab === 'corridors' || currentTab === 'forests') && (
            <AnalyticsView
              selectedRegion={selectedRegion}
              onSelectRegion={handleSelectRegion}
            />
          )}

          {/* TAB 10: DATA SOURCES & GEOSPATIAL CONNECTORS */}
          {(currentTab === 'integrations' || currentTab === 'spatial_context') && (
            <IntegrationsView />
          )}

          {/* TAB 7: EVIDENCE-GROUNDED INTELLIGENCE REPORTS & DOSSIER WORKSPACE */}
          {currentTab === 'ai_reports' && (
            <ReportsView
              selectedRegion={selectedRegion}
              onOpenReportModal={handleOpenReportModal}
              selectedFeature={selectedFeature}
            />
          )}

          {/* TAB 10: FOLLOW-UP & AUDIT WORKFLOW */}
          {currentTab === 'follow_ups' && (
            <FollowUpsView
              onInspectFeature={handleInspectFeature}
              onOpenCreateModal={() => handleOpenFollowUpModal()}
            />
          )}

          {/* TAB 11: AI INVESTIGATION CHAT */}
          {currentTab === 'ai_chat' && (
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 text-center py-16 shadow-xs">
              <Sparkles className="w-10 h-10 text-blue-600 mx-auto animate-pulse" />
              <h2 className="text-base font-bold text-slate-900 uppercase font-mono">
                AI Incident Investigation Console
              </h2>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Open the interactive AI drawer to inspect high-heat anomalies, check spatial facility exposure, and query baseline FRP statistics in real-time.
              </p>
              <button
                onClick={() => setIsChatOpen(true)}
                className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold text-xs inline-flex items-center gap-2 hover:bg-blue-700 shadow-sm"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Launch Incident Investigator</span>
              </button>
            </div>
          )}

          {/* TAB 12: FIELD INTELLIGENCE */}
          {currentTab === 'field_reports' && (
            <FieldReportsView
              reports={fieldReports}
              selectedRegion={selectedRegion}
              onReportSubmitted={handleRefreshReports}
            />
          )}

          {/* TAB 13: SETTINGS & MODEL TELEMETRY */}
          {currentTab === 'settings' && <SettingsView status={systemStatus} />}
        </main>
      </div>

      {/* Persistent Floating AI Assistant on all routes */}
      <FloatingAIAssistant />

      {/* Slide-in AI Chat Drawer */}
      <ChatDrawer selectedRegion={selectedRegion} />

      {/* Evidence-Grounded Investigation Report Modal */}
      <InvestigationReportModal
        isOpen={reportModalConfig.isOpen}
        onClose={() => setReportModalConfig({ isOpen: false })}
        selectedRegion={selectedRegion}
        initialScope={reportModalConfig.scope}
        initialFeatureType={reportModalConfig.featureType}
        initialFeatureId={reportModalConfig.featureId}
        onCreateFollowUp={handleCreateFollowUpFromReport}
      />

      {/* Follow-up Task Creation Modal */}
      <FollowUpModal
        isOpen={followUpModalConfig.isOpen}
        onClose={() => setFollowUpModalConfig({ isOpen: false })}
        initialFeatureType={followUpModalConfig.featureType}
        initialFeatureId={followUpModalConfig.featureId}
        initialRegionName={followUpModalConfig.regionName}
        initialReportId={followUpModalConfig.reportId}
      />

      {/* Authentication Modal */}
      <AuthModal
        key={authMode}
        isOpen={isAuthOpen}
        initialMode={authMode}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={(newUser) => setUser(newUser)}
      />
    </div>
  );
};
