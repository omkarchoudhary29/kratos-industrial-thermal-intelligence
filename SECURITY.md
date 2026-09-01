# Security Policy

## Supported Versions

| Version | Supported | Security Maintenance |
|---|---|---|
| KRATOS V3.1 (Latest) | :white_check_mark: | Full Active Security & Bugfix Support |
| KRATOS V3.0 | :x: | Deprecated |
| KRATOS V2.x / V1.x | :x: | End of Life |

## Security Architecture & Defenses

KRATOS V3.1 incorporates several enterprise-grade security controls:

1. **Authentication & Token Rotation:**
   - Stateless JWT access tokens (15-minute lifetime) paired with cryptographically hashed, rotating refresh tokens stored in PostgreSQL.
2. **Brute-Force & Rate Limiting:**
   - Thread-safe sliding-window rate limiting on authentication routes (5 req/min), report synthesis (10 req/min), and AI chats (20 req/min).
3. **SSRF Protection:**
   - External data connectors undergo strict DNS resolution and CIDR range validation to prevent Server-Side Request Forgery against internal networks, AWS/GCP metadata endpoints (`169.254.169.254`), and loopback addresses.
4. **Cryptographic Audit Hash Chaining:**
   - Administrative and operational actions are logged to `system_audit_logs` with HMAC-SHA256 predecessor hash chaining, backed by PostgreSQL triggers rejecting unauthorized updates or deletions.
5. **Least-Privilege Database Accounts:**
   - Dedicated application service accounts (`wildfire_app_user`) restricted from schema drops or superuser commands.
6. **Public Demonstration Protections:**
   - When deployed with `APP_MODE=demo`, statutory authority submissions and external connector modifications are locked to prevent unauthorized tampering.

## Reporting a Security Vulnerability

If you discover a security vulnerability in KRATOS, please do **NOT** open a public issue.

Please report vulnerabilities privately to the project maintainers. Include:
- Description of the vulnerability.
- Steps to reproduce or proof-of-concept payload.
- Potential impact and affected endpoints.

We will review your submission and provide an initial response within 48 hours.
