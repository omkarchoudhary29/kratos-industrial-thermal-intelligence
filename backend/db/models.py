from db.connection import db
from geoalchemy2 import Geometry, WKTElement
from sqlalchemy.types import TypeDecorator, Text
import bcrypt


class SafeGeometry(TypeDecorator):
    """Dialect-adaptive geometry type.

    Uses native PostGIS Geometry on PostgreSQL, and Text on SQLite/other
    dialects so local development runs without requiring a local PostGIS setup.
    """
    impl = Text
    cache_ok = True
    spatial_index = True

    def __init__(self, geometry_type="GEOMETRY", srid=4326, spatial_index=True, **kwargs):
        self.geometry_type = geometry_type
        self.srid = srid
        self.spatial_index = spatial_index
        self.kwargs = kwargs
        self._geom = Geometry(geometry_type, srid=srid, spatial_index=spatial_index, **kwargs)
        super().__init__()

    @property
    def dimension(self):
        return self._geom.dimension

    @property
    def use_typmod(self):
        return self._geom.use_typmod

    @property
    def management(self):
        return getattr(self._geom, "management", False)

    @property
    def as_binary(self):
        return getattr(self._geom, "as_binary", "ST_AsEWKB")

    @property
    def use_N_D_index(self):
        return getattr(self._geom, "use_N_D_index", False)

    def load_dialect_impl(self, dialect):
        if dialect is not None and getattr(dialect, "name", None) == "postgresql":
            return dialect.type_descriptor(self._geom)
        if dialect is None:
            return self._geom
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        dialect_name = getattr(dialect, "name", None) if dialect is not None else None
        if dialect_name != "postgresql" and isinstance(value, WKTElement):
            return str(value.data)
        return value

    def process_result_value(self, value, dialect):
        dialect_name = getattr(dialect, "name", None) if dialect is not None else None
        if dialect_name != "postgresql" and value is not None and not isinstance(value, WKTElement):
            return WKTElement(str(value), srid=self.srid)
        return value


class User(db.Model):
    __tablename__ = 'users'
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(128), nullable=False)
    email           = db.Column(db.String(255), unique=True, nullable=True, index=True)
    is_admin        = db.Column(db.Boolean, nullable=False, default=False)
    chat_count      = db.Column(db.Integer, nullable=False, default=0)
    chat_count_date = db.Column(db.Date, nullable=True)
    created_at      = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), self.password_hash.encode('utf-8')
            )
        except (TypeError, ValueError):
            # Migrated provider-only identities have a deliberately unusable hash.
            return False


class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    jti             = db.Column(db.String(36), unique=True, nullable=False)
    family_id       = db.Column(db.String(36), nullable=False, index=True)
    expires_at      = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at      = db.Column(db.DateTime(timezone=True), nullable=True)
    replaced_by_id = db.Column(db.Integer, db.ForeignKey('refresh_tokens.id'), nullable=True)
    created_at      = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True, cascade='all, delete-orphan'))


class FireEvent(db.Model):
    __tablename__ = "fire_events"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.Text, nullable=False)
    year        = db.Column(db.Integer)
    bbox        = db.Column(SafeGeometry("POLYGON", srid=4326))
    start_date  = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)

    # Pipeline mode control:
    #   NULL  → Realtime: pipeline fetches latest data on each run
    #   value → Replay:   historical analysis up to this date (inclusive)
    end_date    = db.Column(db.Date, nullable=True)

    # Admin-controlled shared replay clock (ms since epoch). NULL = start of event.
    replay_ms   = db.Column(db.BigInteger, nullable=True)

    timesteps   = db.relationship("EventTimestep", backref="event", lazy=True)

    @property
    def is_realtime(self) -> bool:
        return self.end_date is None


class EventTimestep(db.Model):
    __tablename__ = "event_timesteps"
    __table_args__ = (
        db.UniqueConstraint(
            "event_id", "slot_time", name="uq_event_timesteps_event_slot"
        ),
    )

    id         = db.Column(db.Integer, primary_key=True)
    event_id   = db.Column(db.Integer, db.ForeignKey("fire_events.id"), nullable=False)

    # Canonical 3-hour slot on the regular time grid
    slot_time  = db.Column(db.DateTime(timezone=True), nullable=False)

    # Most recent satellite overpass at or before slot_time (the T1 used for prediction)
    nearest_t1 = db.Column(db.DateTime(timezone=True), nullable=False)

    # Hours between slot_time and nearest_t1 (always >= 0)
    gap_hours      = db.Column(db.Float, nullable=False, default=0.0)

    # True when gap_hours > 12 — prediction may be stale
    data_gap_warn  = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())


# Near-real-time FIRMS persistence.  These tables are intentionally separate
# from ``FireEvent`` above: that entity represents configured analysis regions,
# while a monitoring event represents one physical thermal incident.
class MonitoringFireEvent(db.Model):
    __tablename__ = "monitoring_fire_events"
    __table_args__ = (
        db.Index("ix_monitoring_fire_events_last_detected", "last_detected_at"),
        db.Index("ix_monitoring_fire_events_status", "status"),
        db.Index("ix_monitoring_fire_events_region", "monitoring_region_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    monitoring_region_id = db.Column(
        db.Integer, db.ForeignKey("fire_events.id"), nullable=True
    )
    event_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    centroid_latitude = db.Column(db.Float, nullable=False)
    centroid_longitude = db.Column(db.Float, nullable=False)
    location = db.Column(SafeGeometry("POINT", srid=4326), nullable=True)
    first_detected_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_detected_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="NEW")
    detection_count = db.Column(db.Integer, nullable=False, default=1)
    max_frp = db.Column(db.Float, nullable=True)
    average_frp = db.Column(db.Float, nullable=True)
    predicted_class = db.Column(db.String(64), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    alert_status = db.Column(db.String(24), nullable=False, default="NOT_EVALUATED")
    alert_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )


class FireDetection(db.Model):
    __tablename__ = "fire_detections"
    __table_args__ = (
        db.UniqueConstraint("detection_key", name="uq_fire_detections_detection_key"),
        db.Index("ix_fire_detections_acquisition_time", "acquisition_time"),
        db.Index("ix_fire_detections_event_id", "fire_event_id"),
        db.Index("ix_fire_detections_predicted_class", "predicted_class"),
        db.Index("ix_fire_detections_region", "monitoring_region_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    monitoring_region_id = db.Column(
        db.Integer, db.ForeignKey("fire_events.id"), nullable=True
    )
    detection_key = db.Column(db.String(64), nullable=False)
    fire_event_id = db.Column(
        db.Integer, db.ForeignKey("monitoring_fire_events.id"), nullable=True
    )
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location = db.Column(SafeGeometry("POINT", srid=4326), nullable=True)
    acquisition_time = db.Column(db.DateTime(timezone=True), nullable=False)
    received_at = db.Column(db.DateTime(timezone=True), nullable=False)
    data_latency_seconds = db.Column(db.Integer, nullable=False, default=0)
    satellite = db.Column(db.String(32), nullable=False)
    instrument = db.Column(db.String(32), nullable=False)
    source_product = db.Column(db.String(64), nullable=True)
    brightness = db.Column(db.Float, nullable=True)
    bright_ti4 = db.Column(db.Float, nullable=True)
    bright_ti5 = db.Column(db.Float, nullable=True)
    frp = db.Column(db.Float, nullable=True)
    firms_confidence = db.Column(db.String(32), nullable=True)
    day_night = db.Column(db.String(8), nullable=True)
    land_cover = db.Column(db.String(64), nullable=True)
    landcover_group = db.Column(db.String(32), nullable=True)
    inside_industrial_polygon = db.Column(db.Boolean, nullable=True)
    near_industrial_facility = db.Column(db.Boolean, nullable=True)
    model_features = db.Column(db.JSON, nullable=True)
    predicted_class = db.Column(db.String(64), nullable=True)
    model_confidence = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(64), nullable=False)
    alert_status = db.Column(db.String(24), nullable=False, default="NOT_EVALUATED")
    alert_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now()
    )

    fire_event = db.relationship(
        "MonitoringFireEvent",
        backref=db.backref("detections", lazy=True),
    )


class FireAlert(db.Model):
    __tablename__ = "fire_alerts"
    __table_args__ = (
        db.UniqueConstraint("deduplication_key", name="uq_fire_alerts_deduplication_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    fire_event_id = db.Column(
        db.Integer, db.ForeignKey("monitoring_fire_events.id"), nullable=False, index=True
    )
    detection_id = db.Column(
        db.Integer, db.ForeignKey("fire_detections.id"), nullable=True
    )
    alert_type = db.Column(db.String(32), nullable=False)
    severity = db.Column(db.String(16), nullable=False)
    message = db.Column(db.Text, nullable=False)
    deduplication_key = db.Column(db.String(128), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


class FirmsSyncState(db.Model):
    __tablename__ = "firms_sync_state"

    id = db.Column(db.Integer, primary_key=True, default=1)
    status = db.Column(db.String(24), nullable=False, default="never")
    last_attempt_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_successful_sync = db.Column(db.DateTime(timezone=True), nullable=True)
    records_received = db.Column(db.Integer, nullable=False, default=0)
    new_records = db.Column(db.Integer, nullable=False, default=0)
    duplicates = db.Column(db.Integer, nullable=False, default=0)
    prediction_failures = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.Text, nullable=True)


# 2. Crowd intelligence ────────────────────────────────────────────────────────

class Theme(db.Model):
    __tablename__ = 'themes'
    id         = db.Column(db.Integer, primary_key=True)
    event_id   = db.Column(db.Integer, db.ForeignKey('fire_events.id'), nullable=True)

    center_lat = db.Column(db.Float, nullable=False)
    center_lon = db.Column(db.Float, nullable=False)
    radius_m   = db.Column(db.Float, nullable=False, default=1000.0)

    title      = db.Column(db.Text, nullable=False)
    summary    = db.Column(db.Text, nullable=False)

    like_count   = db.Column(db.Integer, nullable=False, default=0)
    generated_at = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())

    reports  = db.relationship('FieldReport', backref='theme', lazy=True,
                               foreign_keys='FieldReport.theme_id')
    comments = db.relationship('ThemeComment', backref='theme', lazy=True)


class FieldReport(db.Model):
    __tablename__ = 'field_reports'
    id       = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('fire_events.id'), nullable=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('users.id'),       nullable=True)

    # 'fire_report' | 'info' | 'request_help' | 'offer_help'
    post_type   = db.Column(db.Text, nullable=False)
    lat         = db.Column(db.Float, nullable=False)
    lon         = db.Column(db.Float, nullable=False)
    bearing     = db.Column(db.Float, nullable=True)   # degrees from EXIF (fire_report only)
    photo_path  = db.Column(db.Text,  nullable=True)
    description = db.Column(db.Text,  nullable=True)

    # AI-assessed intensity (background, set after insert)
    # 'low' | 'mid' | 'high' | null
    ai_intensity = db.Column(db.Text, nullable=True)

    # Community interaction
    like_count = db.Column(db.Integer, nullable=False, default=0)
    flag_count = db.Column(db.Integer, nullable=False, default=0)

    # Set when report is absorbed into a theme cluster
    theme_id   = db.Column(db.Integer, db.ForeignKey('themes.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    comments = db.relationship('FieldReportComment', backref='report', lazy=True)


class FieldReportComment(db.Model):
    __tablename__ = 'field_report_comments'
    id        = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('field_reports.id'), nullable=False)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    content    = db.Column(db.Text, nullable=False)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class ThemeComment(db.Model):
    __tablename__ = 'theme_comments'
    id       = db.Column(db.Integer, primary_key=True)
    theme_id = db.Column(db.Integer, db.ForeignKey('themes.id'), nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey('users.id'),  nullable=True)

    content    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class OSMFacility(db.Model):
    __tablename__ = "osm_facilities"
    __table_args__ = (
        db.UniqueConstraint("osm_type", "osm_id", name="uq_osm_facilities_type_id"),
        db.Index("ix_osm_facilities_geom", "geometry"),
        db.Index("ix_osm_facilities_centroid", "centroid"),
        db.Index("ix_osm_facilities_region_id", "region_id"),
        db.Index("ix_osm_facilities_category", "facility_category"),
    )

    id = db.Column(db.BigInteger, primary_key=True)
    osm_id = db.Column(db.BigInteger, nullable=False)
    osm_type = db.Column(db.String(16), nullable=False)  # 'node', 'way', 'relation'
    name = db.Column(db.Text, nullable=True)
    facility_category = db.Column(db.String(64), nullable=False)
    subcategory = db.Column(db.String(64), nullable=True)
    region_id = db.Column(db.Integer, db.ForeignKey("fire_events.id"), nullable=True)
    region_name = db.Column(db.String(128), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    geometry = db.Column(SafeGeometry("GEOMETRY", srid=4326), nullable=False)
    centroid = db.Column(SafeGeometry("POINT", srid=4326), nullable=False)
    source = db.Column(db.String(32), default="osm_overpass")
    retrieved_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


class InvestigationReport(db.Model):
    __tablename__ = "investigation_reports"
    __table_args__ = (
        db.Index("ix_investigation_reports_scope", "scope"),
        db.Index("ix_investigation_reports_region_id", "region_id"),
        db.Index("ix_investigation_reports_feature", "feature_type", "feature_id"),
        db.Index("ix_investigation_reports_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    report_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    scope = db.Column(db.String(32), nullable=False)  # 'region', 'viewport', 'feature'
    region_id = db.Column(db.String(64), nullable=True)
    region_name = db.Column(db.String(128), nullable=True)
    feature_type = db.Column(db.String(32), nullable=True)  # 'cluster', 'observation', 'facility'
    feature_id = db.Column(db.String(64), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    bounds = db.Column(db.JSON, nullable=True)
    time_range_start = db.Column(db.DateTime(timezone=True), nullable=True)
    time_range_end = db.Column(db.DateTime(timezone=True), nullable=True)
    evidence_payload = db.Column(db.JSON, nullable=False)
    summary_text = db.Column(db.Text, nullable=True)
    sections = db.Column(db.JSON, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    creator_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(32), default="generated")
    version = db.Column(db.String(16), default="v1.0")
    pdf_path = db.Column(db.String(255), nullable=True)
    csv_path = db.Column(db.String(255), nullable=True)
    submission_status = db.Column(db.String(32), default="NOT_SUBMITTED")
    approval_trail = db.Column(db.JSON, nullable=True)
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    follow_ups = db.relationship("FollowUpTask", backref="report", lazy=True)
    submissions = db.relationship("AuthoritySubmission", backref="report", lazy=True)


class FollowUpTask(db.Model):
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        db.Index("ix_follow_up_tasks_status", "status"),
        db.Index("ix_follow_up_tasks_priority", "priority"),
        db.Index("ix_follow_up_tasks_feature", "feature_type", "feature_id"),
        db.Index("ix_follow_up_tasks_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    task_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    feature_type = db.Column(db.String(32), nullable=False)  # 'cluster', 'observation', 'facility', 'region'
    feature_id = db.Column(db.String(64), nullable=False)
    region_name = db.Column(db.String(128), nullable=True)
    report_id = db.Column(db.Integer, db.ForeignKey("investigation_reports.id"), nullable=True)
    priority = db.Column(db.String(16), nullable=False, default="MEDIUM")  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    status = db.Column(db.String(32), nullable=False, default="OPEN")  # 'OPEN', 'IN_PROGRESS', 'AWAITING_VERIFICATION', 'RESOLVED', 'CLOSED'
    description = db.Column(db.Text, nullable=True)
    assigned_to = db.Column(db.String(128), nullable=True)
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_name = db.Column(db.String(128), nullable=False, default="Operational Analyst")
    evidence_attachments = db.Column(db.JSON, nullable=True)
    audit_trail = db.Column(db.JSON, nullable=True)
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    notes = db.relationship("FollowUpNote", backref="task", lazy=True, cascade="all, delete-orphan")


class FollowUpNote(db.Model):
    __tablename__ = "follow_up_notes"
    __table_args__ = (
        db.Index("ix_follow_up_notes_follow_up_id", "follow_up_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    follow_up_id = db.Column(db.Integer, db.ForeignKey("follow_up_tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    author_name = db.Column(db.String(128), nullable=False, default="Operational Analyst")
    note_text = db.Column(db.Text, nullable=False)
    status_change = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


class AuthoritySubmission(db.Model):
    __tablename__ = "authority_submissions"
    __table_args__ = (
        db.Index("ix_authority_submissions_report_id", "report_id"),
        db.Index("ix_authority_submissions_authority_id", "authority_id"),
        db.Index("ix_authority_submissions_status", "status"),
        db.Index("ix_authority_submissions_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    submission_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("investigation_reports.id"), nullable=True)
    report_key = db.Column(db.String(64), nullable=False)
    authority_id = db.Column(db.String(64), nullable=False)
    authority_name = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(128), nullable=False)
    channel = db.Column(db.String(64), nullable=False)  # 'PORTAL', 'EMAIL', 'PHYSICAL_DISPATCH', 'API'
    reference_number = db.Column(db.String(128), nullable=False)
    acknowledgement_number = db.Column(db.String(128), nullable=True)
    submitted_by = db.Column(db.String(128), nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    status = db.Column(db.String(32), nullable=False, default="SUBMITTED")
    notes = db.Column(db.Text, nullable=True)
    receipt_metadata = db.Column(db.JSON, nullable=True)
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())


class DataConnector(db.Model):
    __tablename__ = "data_connectors"
    __table_args__ = (
        db.Index("ix_data_connectors_key", "connector_key"),
        db.Index("ix_data_connectors_health", "health_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    connector_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(255), nullable=False)
    connector_type = db.Column(db.String(64), nullable=False)
    endpoint_url = db.Column(db.Text, nullable=False)
    auth_type = db.Column(db.String(32), nullable=False, default="NONE")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    health_status = db.Column(db.String(32), nullable=False, default="HEALTHY")
    last_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    records_received = db.Column(db.Integer, default=0)
    records_accepted = db.Column(db.Integer, default=0)
    records_rejected = db.Column(db.Integer, default=0)
    configuration = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    sync_jobs = db.relationship("IntegrationSyncJob", backref="connector", lazy=True, cascade="all, delete-orphan")


class IntegrationSyncJob(db.Model):
    __tablename__ = "integration_sync_jobs"
    __table_args__ = (
        db.Index("ix_integration_sync_jobs_connector_id", "connector_id"),
        db.Index("ix_integration_sync_jobs_status", "status"),
        db.Index("ix_integration_sync_jobs_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    job_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    connector_id = db.Column(db.Integer, db.ForeignKey("data_connectors.id", ondelete="CASCADE"), nullable=False)
    connector_key = db.Column(db.String(64), nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    end_time = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="RUNNING")
    records_fetched = db.Column(db.Integer, default=0)
    records_accepted = db.Column(db.Integer, default=0)
    duplicates_dropped = db.Column(db.Integer, default=0)
    records_rejected = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    checkpoint_timestamp = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


class SystemAuditLog(db.Model):
    __tablename__ = "system_audit_logs"
    __table_args__ = (
        db.Index("ix_system_audit_logs_timestamp", "timestamp"),
        db.Index("ix_system_audit_logs_action", "action_type"),
        db.Index("ix_system_audit_logs_user_id", "user_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(128), nullable=False)
    user_role = db.Column(db.String(64), nullable=False, default="Monitoring Analyst")
    action_type = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.String(128), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="SUCCESS")
    details = db.Column(db.JSON, nullable=True)
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)
    previous_record_hash = db.Column(db.String(64), nullable=True)
    integrity_hash = db.Column(db.String(64), nullable=True)
    integrity_version = db.Column(db.String(16), nullable=False, default="v2_chain")
    hash_backfilled_at = db.Column(db.DateTime(timezone=True), nullable=True)


