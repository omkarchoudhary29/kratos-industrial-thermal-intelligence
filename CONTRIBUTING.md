# Contributing to KRATOS V3.1

Thank you for your interest in contributing to KRATOS V3.1 (Industrial Thermal Intelligence & Autonomous Geospatial Surveillance).

## 1. Development Principles

- **Empirical Grounding:** Never state or implement features that claim satellite thermal observations constitute confirmed physical fires without independent ground truth or corroboration.
- **Test-Driven Reliability:** All backend features must include automated test coverage executed against the isolated test database `wildfire_test_db`.
- **Database Safety:** Never run mutating operations, migrations, or tests directly against `wildfire_db`. Always use `.env.test`.
- **Security First:** Never commit credentials, private tokens, passwords, or connection strings. Use environment variables defined in `.env.example`.

## 2. Setting Up Local Environment

1. **Prerequisites:**
   - Python 3.12+
   - Node.js 18+ & npm 9+
   - PostgreSQL 18+ with PostGIS 3.6+
2. **Clone and Branch:**
   ```bash
   git clone <repo-url>
   git checkout -b feature/your-feature-name
   ```
3. **Backend Setup:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   cp .env.example .env
   # Configure database credentials in .env
   ```
4. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 3. Testing Requirements

Before submitting changes, ensure all regression tests pass:

```bash
# Execute full backend test suite against wildfire_test_db
pytest backend/tests/ -v

# Verify frontend TypeScript build
npm --prefix frontend run build
```

## 4. Pull Request Guidelines

1. Ensure commit messages are descriptive and concise.
2. Keep PRs focused on a single capability, bugfix, or enhancement.
3. Update relevant documentation in `docs/` and `CHANGELOG.md`.
4. Ensure no secret or credential files (`.env`, `.env.test`, `.admin_credentials.local`) are staged.
