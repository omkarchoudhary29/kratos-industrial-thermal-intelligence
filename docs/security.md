# KRATOS V3.1 — Security Architecture & Threat Model

This document outlines the defense-in-depth security model implemented in KRATOS V3.1.

## 1. Authentication & Session Management

- **Access Tokens:** Stateless JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`). Default lifetime: 15 minutes (`JWT_ACCESS_TOKEN_MINUTES=15`).
- **Refresh Tokens:** Cryptographically hashed (SHA-256) random tokens stored in PostgreSQL with family ID tracking and automatic rotation to defend against token theft.
- **Password Storage:** Salted and hashed using `bcrypt` (12 rounds) with maximum byte-length guards (72 bytes).

## 2. Sliding-Window Rate Limiter & Brute-Force Defense

Implemented in `backend/utils/rate_limiter.py` using thread-safe in-memory sliding windows:
- `/auth/login`: 5 requests per 60 seconds (keyed by IP + identifier).
- `/api/v1/reports/generate`: 10 requests per 60 seconds (keyed by user/IP).
- `/events/<id>/chat`: 20 requests per 60 seconds (keyed by user/IP).
- Responds with HTTP 429 Too Many Requests and RFC-compliant `Retry-After` header.

## 3. Server-Side Request Forgery (SSRF) Defense

For external integrations (`backend/api/integrations.py`), all remote URLs undergo strict validation before outbound requests:
- Prohibits loopback IP addresses (`127.0.0.0/8`, `::1`).
- Prohibits private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- Prohibits cloud metadata endpoints (`169.254.169.254`).
- Enforces strict URI schemes (`http`, `https`).

## 4. Cryptographic Audit Log Chaining

Audit events recorded in `system_audit_logs` are protected by an immutable hash chain:
- Each record computes:
  $$\text{Hash}_i = \text{HMAC-SHA256}(K, \text{PredecessorHash}_{i-1} \parallel \text{Timestamp} \parallel \text{EventType} \parallel \text{Payload})$$
- Backed by PostgreSQL trigger `audit_log_immutability_guard` rejecting updates or deletions.
- API endpoint `GET /api/v1/settings/audit-logs/verify-chain` verifies chain continuity.

## 5. Public Demonstration Restrictions (`APP_MODE=demo`)

When deployed in demonstration mode:
- Statutory authority submissions are blocked (`POST /api/v1/submissions/record` returns HTTP 403).
- External connector registration and sync are blocked.
- General users can safely inspect the live map, generate draft reports, and query the AI Investigator without mutating operational compliance records.
