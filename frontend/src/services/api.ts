import {
  AISituationReport,
  FieldReport,
  LiveFireDetection,
  LiveFireEvent,
  Region,
  SystemStatus,
  ThermalEvent,
  ThermalSource,
  ThermalStats,
  User,
} from '../types';

const ACCESS_TOKEN_KEY = 'iti_access_token';
const REFRESH_TOKEN_KEY = 'iti_refresh_token';

class ApiClient {
  private base = '';
  private refreshPromise: Promise<string> | null = null;

  public getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  public setTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  }

  public clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  public isAuthenticated(): boolean {
    return !!localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  private async fetchWithAuth(url: string, init: RequestInit = {}, canRetry = true): Promise<Response> {
    const headers = new Headers(init.headers || {});
    const token = this.getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    } else {
      headers.set('X-Demo-Mode', 'judge-preview');
    }
    if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const res = await fetch(`${this.base}${url}`, { ...init, headers });

    if (res.status === 401 && canRetry && localStorage.getItem(REFRESH_TOKEN_KEY)) {
      try {
        await this.rotateRefreshToken();
        return this.fetchWithAuth(url, init, false);
      } catch (err) {
        this.clearTokens();
        throw err;
      }
    }

    return res;
  }

  private async rotateRefreshToken(): Promise<string> {
    if (this.refreshPromise) return this.refreshPromise;

    const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refresh) throw new Error('No refresh token available');

    this.refreshPromise = (async () => {
      const res = await fetch(`${this.base}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        this.clearTokens();
        throw new Error('Refresh token expired');
      }
      const data = await res.json();
      this.setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    })().finally(() => {
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  private async request<T>(url: string, init: RequestInit = {}): Promise<T> {
    const res = await this.fetchWithAuth(url, init);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.message || err.error || `HTTP ${res.status}`);
    }
    return res.status === 204 ? (null as T) : res.json();
  }

  // ── Authentication ───────────────────────────────────────────────────────────
  public async login(identifier: string, password: string): Promise<{ user: User; access_token: string }> {
    const res = await fetch(`${this.base}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, username: identifier, email: identifier, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Login failed' }));
      throw new Error(err.message || err.error || 'Invalid email or password.');
    }
    const data = await res.json();
    this.setTokens(data.access_token, data.refresh_token);
    return data;
  }

  public async register(username: string, password: string, email?: string): Promise<{ user: User; access_token: string }> {
    const res = await fetch(`${this.base}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Registration failed' }));
      throw new Error(err.message || err.error || 'Registration failed');
    }
    const data = await res.json();
    this.setTokens(data.access_token, data.refresh_token);
    return data;
  }

  public async getMe(): Promise<User | null> {
    if (!this.getAccessToken()) return null;
    try {
      return await this.request<User>('/auth/me');
    } catch {
      this.clearTokens();
      return null;
    }
  }

  public async logout(): Promise<void> {
    const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (refresh) {
      await fetch(`${this.base}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      }).catch(() => {});
    }
    this.clearTokens();
  }

  // ── Public Configuration ───────────────────────────────────────────────────
  public async getConfig(): Promise<{ sentinel_enabled?: boolean; carto_api_key?: string | null }> {
    try {
      return await this.request<{ sentinel_enabled?: boolean; carto_api_key?: string | null }>('/api/config/');
    } catch {
      return {};
    }
  }

  // ── Monitoring Catalog & Regions ─────────────────────────────────────────────
  public async getRegions(): Promise<Region[]> {
    try {
      const list = await this.request<any[]>('/api/regions/');
      return list.map((r) => ({
        id: r.id || r.region_id,
        name: r.name,
        category: (r.monitoring_focus || '').toLowerCase().includes('forest')
          ? 'forest_landscape'
          : 'industrial_corridor',
        state: r.state || 'India',
        description: r.description || '',
        center: r.center || [20.5937, 78.9629],
        zoom: r.default_zoom || 10,
        bbox: r.bbox || [68.1, 8.0, 97.4, 37.0],
        event_id: r.event_id,
      }));
    } catch {
      // Fallback region catalogue if offline
      return [
        { id: 'vijayanagar', name: 'Vijayanagar / Toranagallu', category: 'industrial_corridor', state: 'Karnataka', description: 'JSW Steel Complex and metallurgical hub', center: [15.2, 76.66], zoom: 11, bbox: [76.5, 15.0, 76.9, 15.4], event_id: 2 },
        { id: 'talcher_angul', name: 'Talcher / Angul', category: 'industrial_corridor', state: 'Odisha', description: 'Coalfields, NTPC power stations & aluminum smelters', center: [20.85, 85.15], zoom: 10, bbox: [84.9, 20.7, 85.4, 21.1], event_id: 3 },
        { id: 'dhanbad_bokaro', name: 'Dhanbad / Bokaro', category: 'industrial_corridor', state: 'Jharkhand', description: 'BCCL coking coalfields, SAIL steelworks', center: [23.75, 86.15], zoom: 10, bbox: [85.9, 23.5, 86.4, 24.0], event_id: 4 },
        { id: 'singrauli_sonbhadra', name: 'Singrauli / Sonbhadra', category: 'industrial_corridor', state: 'MP / UP', description: 'Northern coalfields and thermal super-plants', center: [24.1, 82.6], zoom: 10, bbox: [82.3, 23.8, 83.0, 24.4], event_id: 5 },
        { id: 'korba', name: 'Korba Industrial Hub', category: 'industrial_corridor', state: 'Chhattisgarh', description: 'SECL coal operations and power basin', center: [22.35, 82.7], zoom: 10, bbox: [82.4, 22.1, 83.0, 22.6], event_id: 6 },
        { id: 'jamnagar_vadinar', name: 'Jamnagar / Vadinar', category: 'industrial_corridor', state: 'Gujarat', description: 'Reliance and Nayara mega refinery complexes', center: [22.45, 69.85], zoom: 10, bbox: [69.6, 22.2, 70.2, 22.7], event_id: 7 },
        { id: 'gadchiroli_tadoba', name: 'Gadchiroli / Tadoba', category: 'forest_landscape', state: 'Maharashtra', description: 'Tiger reserve corridors and deciduous forest range', center: [20.15, 79.9], zoom: 9, bbox: [79.4, 19.5, 80.5, 20.8], event_id: 8 },
        { id: 'kanha_pench', name: 'Kanha / Pench', category: 'forest_landscape', state: 'Madhya Pradesh', description: 'Central highland wildlife and forest corridor', center: [22.0, 80.2], zoom: 9, bbox: [79.6, 21.4, 80.8, 22.6], event_id: 9 },
        { id: 'bastar', name: 'Bastar Woodlands', category: 'forest_landscape', state: 'Chhattisgarh', description: 'Dense sal forest canopy and tribal belt', center: [19.1, 81.6], zoom: 9, bbox: [81.0, 18.5, 82.2, 19.8], event_id: 10 },
        { id: 'mizoram', name: 'Mizoram Hill Forests', category: 'forest_landscape', state: 'Mizoram', description: 'Subtropical montane forests and shifting agriculture terrain', center: [23.3, 92.8], zoom: 9, bbox: [92.2, 22.5, 93.4, 24.1], event_id: 11 },
      ];
    }
  }

  // ── Thermal Analytics & Parquet Artifacts ─────────────────────────────────────
  public async getThermalStats(filters: {
    region?: string;
    year?: number;
    data_mode?: string;
    start_time?: string;
    end_time?: string;
  } | string = {}): Promise<ThermalStats> {
    const params = new URLSearchParams();
    if (typeof filters === 'string') {
      params.set('region', filters);
    } else {
      if (filters.region) params.set('region', filters.region);
      if (filters.year) params.set('year', String(filters.year));
      if (filters.data_mode) params.set('data_mode', filters.data_mode);
      if (filters.start_time) params.set('start_time', filters.start_time);
      if (filters.end_time) params.set('end_time', filters.end_time);
    }
    return this.request<ThermalStats>(`/api/v1/thermal/stats?${params.toString()}`);
  }

  public async getThermalEvents(filters: {
    region?: string;
    risk_level?: string;
    limit?: number;
    offset?: number;
    iforest_agreement?: boolean;
    data_mode?: string;
    start_time?: string;
    end_time?: string;
  } = {}): Promise<{ total: number; events: ThermalEvent[] }> {
    const params = new URLSearchParams();
    if (filters.region) params.set('region', filters.region);
    if (filters.risk_level) params.set('risk_level', filters.risk_level);
    if (filters.limit) params.set('limit', String(filters.limit));
    if (filters.offset) params.set('offset', String(filters.offset));
    if (filters.iforest_agreement !== undefined) params.set('iforest_agreement', String(filters.iforest_agreement));
    if (filters.data_mode) params.set('data_mode', filters.data_mode);
    if (filters.start_time) params.set('start_time', filters.start_time);
    if (filters.end_time) params.set('end_time', filters.end_time);

    const data = await this.request<any>(`/api/v1/thermal/events?${params.toString()}`);
    return {
      total: data.total || (Array.isArray(data) ? data.length : 0),
      events: data.events || (Array.isArray(data) ? data : []),
    };
  }

  public async getFeatureDetail(
    type: string,
    id: string,
    lat?: number,
    lon?: number
  ): Promise<import('../types').FeatureDetailResponse> {
    const q = new URLSearchParams({ type, id });
    if (lat !== undefined && lat !== null) q.set('lat', String(lat));
    if (lon !== undefined && lon !== null) q.set('lon', String(lon));
    return this.request<import('../types').FeatureDetailResponse>(
      `/api/v1/intelligence/feature-detail?${q.toString()}`
    );
  }

  public async getThermalMapEvents(filters: {
    region?: string;
    risk_level?: string;
    limit?: number;
  } = {}): Promise<ThermalEvent[]> {
    const params = new URLSearchParams();
    if (filters.region) params.set('region', filters.region);
    if (filters.risk_level) params.set('risk_level', filters.risk_level);
    if (filters.limit) params.set('limit', String(filters.limit));
    const data = await this.request<any>(`/api/v1/thermal/map?${params.toString()}`);
    return Array.isArray(data) ? data : data.events || [];
  }

  public async getThermalSources(region?: string, limit = 500): Promise<ThermalSource[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (region) params.set('region', region);
    const data = await this.request<any>(`/api/v1/thermal/sources?${params.toString()}`);
    return Array.isArray(data) ? data : data.sources || [];
  }

  // ── Near-Real-Time FIRMS Feeds ────────────────────────────────────────────────
  public async getRecentFireDetections(hours = 24, regionEventId?: number): Promise<LiveFireDetection[]> {
    const params = new URLSearchParams({ hours: String(hours) });
    if (regionEventId) params.set('region_event_id', String(regionEventId));
    const data = await this.request<any>(`/api/fires/recent?${params.toString()}`);
    return Array.isArray(data) ? data : data.detections || [];
  }

  public async getRecentFireEvents(hours = 24, regionEventId?: number): Promise<LiveFireEvent[]> {
    const params = new URLSearchParams({ hours: String(hours) });
    if (regionEventId) params.set('region_event_id', String(regionEventId));
    const data = await this.request<any>(`/api/fires/events?${params.toString()}`);
    return Array.isArray(data) ? data : data.events || [];
  }

  public async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/api/fires/status');
  }

  // ── Field Reports ─────────────────────────────────────────────────────────────
  public async getFieldReports(eventId = 2): Promise<FieldReport[]> {
    try {
      const data = await this.request<any>(`/api/events/${eventId}/field-reports`);
      return Array.isArray(data) ? data : data.reports || [];
    } catch {
      return [];
    }
  }

  public async submitFieldReport(eventId: number, data: FormData | object): Promise<FieldReport> {
    const isForm = data instanceof FormData;
    const res = await this.fetchWithAuth(`/api/events/${eventId}/field-reports`, {
      method: 'POST',
      body: isForm ? data : JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Submission failed' }));
      throw new Error(err.message || err.error || 'Failed to submit report');
    }
    return res.json();
  }

  // ── AI Reporting & Streaming Investigation ───────────────────────────────────
  public async generateReport(eventId = 2, force = false): Promise<AISituationReport> {
    const res = await this.request<any>(`/api/events/${eventId}/timesteps/1/report`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
    return res;
  }

  public streamChat(
    eventId: number,
    payload: {
      message: string;
      timestep_id?: number;
      history?: Array<{ role: string; content: string }>;
      selected_feature?: {
        feature_type: string;
        feature_id: string;
      };
    },
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (err: string) => void
  ): () => void {
    const controller = new AbortController();

    this.fetchWithAuth(`/api/events/${eventId}/chat`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const e = await res.json().catch(() => ({ error: res.statusText }));
          onError(e.message || e.error || `HTTP ${res.status}`);
          return;
        }
        const reader = res.body?.getReader();
        if (!reader) {
          onError('Stream reader unavailable');
          return;
        }
        const decoder = new TextDecoder();
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          if (value) onChunk(decoder.decode(value));
        }
        onDone();
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError(err.message || 'Stream connection broken');
      });

    return () => controller.abort();
  }

  // ── OSM Facilities Overlays ──────────────────────────────────────────────────
  public async getOsmFacilities(params?: {
    region_id?: number;
    category?: string;
    bbox?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('../types').OSMFacilityCollection> {
    const q = new URLSearchParams();
    if (params?.region_id) q.set('region_id', String(params.region_id));
    if (params?.category) q.set('category', params.category);
    if (params?.bbox) q.set('bbox', params.bbox);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));

    const qs = q.toString();
    return this.request<import('../types').OSMFacilityCollection>(
      `/api/v1/osm/facilities${qs ? `?${qs}` : ''}`
    );
  }

  public async getOsmCategories(region_id?: number): Promise<{ categories: Array<{ category: string; count: number }> }> {
    const qs = region_id ? `?region_id=${region_id}` : '';
    return this.request<{ categories: Array<{ category: string; count: number }> }>(
      `/api/v1/osm/categories${qs}`
    );
  }

  // ── Investigation Reports ───────────────────────────────────────────────────
  public async generateInvestigationReport(payload: {
    scope: 'region' | 'viewport' | 'feature';
    region_id?: number;
    region_name?: string;
    bounds?: Record<string, number>;
    feature_type?: string;
    feature_id?: string;
    title?: string;
  }): Promise<import('../types').InvestigationReportData> {
    return this.request<import('../types').InvestigationReportData>('/api/v1/reports/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async listInvestigationReports(params?: {
    scope?: string;
    region?: string;
    feature_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ reports: import('../types').InvestigationReportData[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.scope) q.set('scope', params.scope);
    if (params?.region) q.set('region', params.region);
    if (params?.feature_id) q.set('feature_id', params.feature_id);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));

    const qs = q.toString();
    return this.request<{ reports: import('../types').InvestigationReportData[]; total: number }>(
      `/api/v1/reports${qs ? `?${qs}` : ''}`
    );
  }

  public async getInvestigationReport(id: string | number): Promise<import('../types').InvestigationReportData> {
    return this.request<import('../types').InvestigationReportData>(`/api/v1/reports/${id}`);
  }

  public getReportPdfDownloadUrl(id: string | number): string {
    return `/api/v1/reports/${id}/pdf`;
  }

  public getReportCsvDownloadUrl(id: string | number): string {
    return `/api/v1/reports/${id}/csv`;
  }

  // ── Follow-Up Task Management ────────────────────────────────────────────────
  public async createFollowUp(payload: {
    title: string;
    feature_type: string;
    feature_id: string;
    region_name?: string;
    report_id?: number | null;
    priority?: import('../types').FollowUpPriority;
    status?: import('../types').FollowUpStatus;
    description?: string;
    assigned_to?: string;
    due_date?: string | null;
  }): Promise<import('../types').FollowUpTaskData> {
    return this.request<import('../types').FollowUpTaskData>('/api/v1/followups', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async listFollowUps(params?: {
    status?: string;
    priority?: string;
    feature_id?: string;
    region?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ tasks: import('../types').FollowUpTaskData[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.priority) q.set('priority', params.priority);
    if (params?.feature_id) q.set('feature_id', params.feature_id);
    if (params?.region) q.set('region', params.region);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));

    const qs = q.toString();
    return this.request<{ tasks: import('../types').FollowUpTaskData[]; total: number }>(
      `/api/v1/followups${qs ? `?${qs}` : ''}`
    );
  }

  public async getFollowUp(id: string | number): Promise<import('../types').FollowUpTaskData> {
    return this.request<import('../types').FollowUpTaskData>(`/api/v1/followups/${id}`);
  }

  public async updateFollowUp(
    id: string | number,
    payload: {
      status?: import('../types').FollowUpStatus;
      priority?: import('../types').FollowUpPriority;
      assigned_to?: string;
      description?: string;
      note?: string;
    }
  ): Promise<import('../types').FollowUpTaskData> {
    return this.request<import('../types').FollowUpTaskData>(`/api/v1/followups/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  public async addFollowUpNote(
    id: string | number,
    payload: {
      note_text: string;
      status_change?: import('../types').FollowUpStatus;
    }
  ): Promise<import('../types').FollowUpNoteData> {
    return this.request<import('../types').FollowUpNoteData>(`/api/v1/followups/${id}/notes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ── Source & Ingestion Freshness ─────────────────────────────────────────────
  public async getFiresStatus(): Promise<import('../types').DataFreshnessInfo> {
    return this.request<import('../types').DataFreshnessInfo>('/api/fires/status');
  }

  // ── Persistent Notification Center ─────────────────────────────────────────
  public async getNotifications(params?: {
    status?: string;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<import('../types').NotificationResponse> {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.severity) q.set('severity', params.severity);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));

    const qs = q.toString();
    return this.request<import('../types').NotificationResponse>(
      `/api/v1/notifications${qs ? `?${qs}` : ''}`
    );
  }

  public async markNotificationRead(alertId: number): Promise<{ id: number; is_read: boolean; read_at: string; unread_count: number }> {
    return this.request(`/api/v1/notifications/${alertId}/read`, {
      method: 'PATCH',
    });
  }

  public async markAllNotificationsRead(): Promise<{ message: string; updated_count: number; unread_count: number }> {
    return this.request('/api/v1/notifications/mark-all-read', {
      method: 'POST',
    });
  }

  // ── Unified Geospatial Global Search ───────────────────────────────────────
  public async search(query: string, limit = 10): Promise<import('../types').SearchResponse> {
    const q = new URLSearchParams();
    q.set('q', query);
    q.set('limit', String(limit));
    return this.request<import('../types').SearchResponse>(`/api/v1/search?${q.toString()}`);
  }

  // ── Phase 2 Advanced Intelligence APIs ───────────────────────────────────────

  public async getSourceFacilityCatalog(params?: {
    region?: string;
    limit?: number;
    offset?: number;
    q?: string;
  }): Promise<{
    total: number;
    count: number;
    sources: import('../types').SourceFacilityItem[];
    facility_association_summary: Record<string, number>;
  }> {
    const q = new URLSearchParams();
    if (params?.region) q.set('region', params.region);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));
    if (params?.q) q.set('q', params.q);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/source-facility/catalog${qs ? `?${qs}` : ''}`);
  }

  public async getThermalAnalysisStats(params?: {
    region?: string;
    source_id?: string;
    start_time?: string;
    end_time?: string;
  }): Promise<import('../types').ThermalAnalysisStats> {
    const q = new URLSearchParams();
    if (params?.region) q.set('region', params.region);
    if (params?.source_id) q.set('source_id', params.source_id);
    if (params?.start_time) q.set('start_time', params.start_time);
    if (params?.end_time) q.set('end_time', params.end_time);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/thermal-analysis/stats${qs ? `?${qs}` : ''}`);
  }

  public async getRecurrenceStats(sourceId: string): Promise<Record<string, any>> {
    return this.request(`/api/v1/intelligence/thermal-analysis/recurrence/${encodeURIComponent(sourceId)}`);
  }

  public async getHistoricalBaseline(params: {
    source_id: string;
    target_time?: string;
    window_days?: number;
  }): Promise<Record<string, any>> {
    const q = new URLSearchParams();
    q.set('source_id', params.source_id);
    if (params.target_time) q.set('target_time', params.target_time);
    if (params.window_days) q.set('window_days', String(params.window_days));
    return this.request(`/api/v1/intelligence/thermal-analysis/baseline?${q.toString()}`);
  }

  public async getTemporalTrends(region?: string): Promise<{
    region: string;
    total_events: number;
    monthly_trends: Array<{
      period: string;
      event_count: number;
      mean_frp_mw: number;
      max_frp_mw: number;
      total_frp_mw: number;
    }>;
  }> {
    const q = new URLSearchParams();
    if (region) q.set('region', region);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/thermal-analysis/trends${qs ? `?${qs}` : ''}`);
  }

  public async getOperationalPriorityQueue(params?: {
    limit?: number;
    region?: string;
  }): Promise<{
    count: number;
    queue: import('../types').OperationalPriorityItem[];
  }> {
    const q = new URLSearchParams();
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.region) q.set('region', params.region);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/risk-evaluation/queue${qs ? `?${qs}` : ''}`);
  }

  public async getComplianceStandards(): Promise<{
    standards: import('../types').ComplianceStandard[];
    disclaimer: string;
  }> {
    return this.request('/api/v1/intelligence/compliance-screening/standards');
  }

  public async screenFacilityCompliance(payload: {
    facility_name: string;
    facility_category: string;
    max_frp_ratio?: number;
    max_frp_mw?: number;
    distance_m?: number;
    detection_count?: number;
    is_anomaly_flagged?: boolean;
  }): Promise<import('../types').ComplianceScreeningResult> {
    return this.request('/api/v1/intelligence/compliance-screening/screen', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async getInvestigations(params?: {
    region?: string;
    limit?: number;
  }): Promise<{
    count: number;
    valid_review_states: string[];
    investigations: import('../types').InvestigationItem[];
  }> {
    const q = new URLSearchParams();
    if (params?.region) q.set('region', params.region);
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/investigations${qs ? `?${qs}` : ''}`);
  }

  public async updateInvestigationStatus(
    id: number,
    status: string,
    notes?: string
  ): Promise<{
    id: number;
    updated_status: string;
    persisted_to_database: boolean;
    timestamp: string;
    message: string;
  }> {
    return this.request(`/api/v1/intelligence/investigations/${id}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, notes: notes || '' }),
    });
  }

  public async getCandidateModelEvaluation(): Promise<import('../types').SupervisedModelEvaluation> {
    return this.request('/api/v1/intelligence/model-evaluation');
  }

  // ── KRATOS V3.1 Enhancement Phase 2 Intelligence APIs ────────────────────────
  public async getEvidenceBundle(params?: {
    source_event_id?: string;
    thermal_source_id?: string;
    latitude?: number;
    longitude?: number;
    frp?: number;
    region?: string;
  }): Promise<{ status: string; evidence_bundle: Record<string, any> }> {
    const q = new URLSearchParams();
    if (params?.source_event_id) q.set('source_event_id', params.source_event_id);
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    if (params?.latitude !== undefined) q.set('latitude', String(params.latitude));
    if (params?.longitude !== undefined) q.set('longitude', String(params.longitude));
    if (params?.frp !== undefined) q.set('frp', String(params.frp));
    if (params?.region) q.set('region', params.region);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/evidence${qs ? `?${qs}` : ''}`);
  }

  public async getFacilityProfile(facilityId: string | number): Promise<{
    status: string;
    facility_profile: Record<string, any>;
  }> {
    return this.request(`/api/v1/intelligence/facility-profile?facility_id=${encodeURIComponent(String(facilityId))}`);
  }

  public async getSourceProfile(sourceId: string): Promise<Record<string, any>> {
    return this.request(`/api/v1/intelligence/source-profile?thermal_source_id=${encodeURIComponent(sourceId)}`);
  }

  public async getMultiLevelBaseline(params?: {
    thermal_source_id?: string;
    facility_id?: string;
    facility_category?: string;
    region?: string;
    point_in_time?: string;
    observed_frp?: number;
  }): Promise<{ status: string; baseline_hierarchy: Record<string, any> }> {
    const q = new URLSearchParams();
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    if (params?.facility_id) q.set('facility_id', params.facility_id);
    if (params?.facility_category) q.set('facility_category', params.facility_category);
    if (params?.region) q.set('region', params.region);
    if (params?.point_in_time) q.set('point_in_time', params.point_in_time);
    if (params?.observed_frp !== undefined) q.set('observed_frp', String(params.observed_frp));
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/historical-baseline${qs ? `?${qs}` : ''}`);
  }

  public async getAnomalies(params?: {
    source_event_id?: string;
    thermal_source_id?: string;
  }): Promise<{ status: string; multi_model_anomaly: Record<string, any>; operational_priority: Record<string, any> }> {
    const q = new URLSearchParams();
    if (params?.source_event_id) q.set('source_event_id', params.source_event_id);
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/anomalies${qs ? `?${qs}` : ''}`);
  }

  public async getHierarchicalClassification(params?: {
    source_event_id?: string;
    thermal_source_id?: string;
  }): Promise<{ status: string; classification: Record<string, any>; facility_context: Record<string, any> }> {
    const q = new URLSearchParams();
    if (params?.source_event_id) q.set('source_event_id', params.source_event_id);
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/classification${qs ? `?${qs}` : ''}`);
  }

  public async getIncidentRisk(params?: {
    source_event_id?: string;
    thermal_source_id?: string;
  }): Promise<{
    status: string;
    incident_ground_truth: Record<string, any>;
    operational_priority: Record<string, any>;
    scientific_distinction: Record<string, any>;
  }> {
    const q = new URLSearchParams();
    if (params?.source_event_id) q.set('source_event_id', params.source_event_id);
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/incident-risk${qs ? `?${qs}` : ''}`);
  }

  public async getExplanations(params?: {
    source_event_id?: string;
    thermal_source_id?: string;
  }): Promise<{
    status: string;
    explainable_summary: string;
    data_gaps: string[];
    deduplication_audit: string;
  }> {
    const q = new URLSearchParams();
    if (params?.source_event_id) q.set('source_event_id', params.source_event_id);
    if (params?.thermal_source_id) q.set('thermal_source_id', params.thermal_source_id);
    const qs = q.toString();
    return this.request(`/api/v1/intelligence/explanations${qs ? `?${qs}` : ''}`);
  }

  // ── Phase 3: Reports, Versions & Approval Lifecycle ─────────────────────────
  public async getReports(params?: {
    scope?: string;
    region?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    total: number;
    limit: number;
    offset: number;
    reports: any[];
  }> {
    const q = new URLSearchParams();
    if (params?.scope) q.set('scope', params.scope);
    if (params?.region) q.set('region', params.region);
    if (params?.status) q.set('status', params.status);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));
    const qs = q.toString();
    return this.request(`/api/v1/reports${qs ? `?${qs}` : ''}`);
  }

  public async getReport(id: string | number): Promise<any> {
    return this.request(`/api/v1/reports/${id}`);
  }

  public async updateReportReviewStatus(
    id: string | number,
    status: string,
    notes?: string
  ): Promise<any> {
    return this.request(`/api/v1/reports/${id}/review-status`, {
      method: 'POST',
      body: JSON.stringify({ status, notes: notes || '' }),
    });
  }

  public async createReportVersion(
    id: string | number,
    version: string,
    notes?: string
  ): Promise<any> {
    return this.request(`/api/v1/reports/${id}/version`, {
      method: 'POST',
      body: JSON.stringify({ version, notes: notes || '' }),
    });
  }

  public getReportPdfUrl(id: string | number): string {
    return `${this.base}/api/v1/reports/${id}/pdf`;
  }

  public getReportCsvUrl(id: string | number): string {
    return `${this.base}/api/v1/reports/${id}/csv`;
  }

  // ── Phase 3: Statutory Authority Submissions ────────────────────────────────
  public async getAuthorities(): Promise<{
    total: number;
    authorities: any[];
    valid_channels: string[];
    valid_statuses: string[];
  }> {
    return this.request('/api/v1/submissions/authorities');
  }

  public async recordAuthoritySubmission(payload: {
    report_id: number;
    authority_id: string;
    purpose?: string;
    channel: string;
    reference_number: string;
    acknowledgement_number?: string;
    submitted_by?: string;
    notes?: string;
  }): Promise<any> {
    return this.request('/api/v1/submissions/record', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async getSubmissions(params?: {
    authority_id?: string;
    status?: string;
    report_id?: number;
  }): Promise<{
    total: number;
    submissions: any[];
  }> {
    const q = new URLSearchParams();
    if (params?.authority_id) q.set('authority_id', params.authority_id);
    if (params?.status) q.set('status', params.status);
    if (params?.report_id) q.set('report_id', String(params.report_id));
    const qs = q.toString();
    return this.request(`/api/v1/submissions${qs ? `?${qs}` : ''}`);
  }

  public async updateSubmissionStatus(
    id: number,
    status: string,
    acknowledgement_number?: string,
    notes?: string
  ): Promise<any> {
    return this.request(`/api/v1/submissions/${id}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, acknowledgement_number, notes }),
    });
  }

  // ── Phase 3: Follow-Up Merging & Idempotency ────────────────────────────────
  public async mergeFollowUps(
    primary_id: number,
    secondary_ids: number[],
    notes?: string
  ): Promise<any> {
    return this.request('/api/v1/followups/merge', {
      method: 'POST',
      body: JSON.stringify({ primary_id, secondary_ids, notes }),
    });
  }

  // ── Phase 3: Advanced Geospatial Analytics ──────────────────────────────────
  public async getAnalyticsOverview(): Promise<any> {
    return this.request('/api/v1/analytics/overview');
  }

  public async getCorridorsAnalytics(): Promise<{ corridors: any[] }> {
    return this.request('/api/v1/analytics/corridors');
  }

  public async getThermalDistribution(): Promise<any> {
    return this.request('/api/v1/analytics/thermal-distribution');
  }

  public async getClassificationBreakdown(): Promise<any> {
    return this.request('/api/v1/analytics/classification-breakdown');
  }

  public async getModelBenchmarks(): Promise<any> {
    return this.request('/api/v1/analytics/models');
  }

  public async getWorkflowKpis(): Promise<any> {
    return this.request('/api/v1/analytics/workflow');
  }

  // ── Phase 3: Data Connectors & Integrations ─────────────────────────────────
  public async getConnectors(): Promise<{ total: number; connectors: any[] }> {
    return this.request('/api/v1/integrations/connectors');
  }

  public async getConnector(id: number): Promise<any> {
    return this.request(`/api/v1/integrations/connectors/${id}`);
  }

  public async testConnection(
    endpoint_url: string,
    auth_type: string = 'NONE',
    headers?: Record<string, string>
  ): Promise<any> {
    return this.request('/api/v1/integrations/test-connection', {
      method: 'POST',
      body: JSON.stringify({ endpoint_url, auth_type, headers }),
    });
  }

  public async registerConnector(data: any): Promise<any> {
    return this.request('/api/v1/integrations/connectors', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async syncConnector(id: number): Promise<any> {
    return this.request(`/api/v1/integrations/connectors/${id}/sync`, {
      method: 'POST',
    });
  }

  public async getSyncJobs(limit?: number): Promise<{ total: number; sync_jobs: any[] }> {
    const q = new URLSearchParams();
    if (limit) q.set('limit', String(limit));
    const qs = q.toString();
    return this.request(`/api/v1/integrations/sync-jobs${qs ? `?${qs}` : ''}`);
  }

  // ── Phase 3: Platform Settings, RBAC & Audit ────────────────────────────────
  public async getUserProfile(): Promise<any> {
    return this.request('/api/v1/settings/profile');
  }

  public async getMonitoringSettings(): Promise<any> {
    return this.request('/api/v1/settings/monitoring');
  }

  public async updateMonitoringSettings(thresholds: Record<string, any>): Promise<any> {
    return this.request('/api/v1/settings/monitoring', {
      method: 'POST',
      body: JSON.stringify(thresholds),
    });
  }

  public async getModelSettings(): Promise<any> {
    return this.request('/api/v1/settings/models');
  }

  public async getAuditLogs(params?: {
    action_type?: string;
    username?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; limit: number; offset: number; logs: any[] }> {
    const q = new URLSearchParams();
    if (params?.action_type) q.set('action_type', params.action_type);
    if (params?.username) q.set('username', params.username);
    if (params?.limit) q.set('limit', String(params.limit));
    if (params?.offset) q.set('offset', String(params.offset));
    const qs = q.toString();
    return this.request(`/api/v1/settings/audit-logs${qs ? `?${qs}` : ''}`);
  }
}

export const api = new ApiClient();
