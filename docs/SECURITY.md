# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Threat Model

HAWKEYE is an **internal tool** deployed on a private VPS with Keycloak RBAC. It is not intended to be
publicly accessible beyond the `/api` and `/` routes exposed through nginx.

## Authentication & Authorisation

- All API routes require a valid **Keycloak JWT** (RS256).
- Three roles: `analyst` (read-only), `supervisor` (triage write), `admin` (all).
- WebSocket connections require the JWT passed as a query param `?token=<jwt>`.
- The frontend uses PKCE; client secret is never shipped to the browser.

## Secrets Management

- All secrets are stored in `.env` (never committed — see `.gitignore`).
- On the VPS, `.env` lives at `/opt/hawkeye/.env` with `chmod 600`.
- GitHub Actions secrets: `VPS_HOST`, `VPS_USER`, `SSH_PRIVATE_KEY`, `ANTHROPIC_API_KEY`.

## Known Limitations (Hackathon Scope)

- No rate limiting on `/api/score` (dev-only endpoint — disable in production).
- Keycloak admin console is accessible on port 8080 (bound to `127.0.0.1` in prod).
- Narrative generation via Claude API — PII in prompts is limited to employee IDs.

## Reporting a Vulnerability

Email: security@nineagents.in
