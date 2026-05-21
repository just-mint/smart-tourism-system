# Security Policy

Security matters for AEGIS O2O because the system handles accounts, order data, uploaded images, and service-to-service credentials.

## Supported Version

The `main` branch is the active development line and is the only supported version unless the team creates release branches later.

## Reporting A Vulnerability

Do not open a public issue with secrets, exploit details, tokens, private database URLs, or user data.

Report security problems privately to the repository maintainers or project owner. Include:

- A short description of the issue.
- Steps to reproduce.
- Affected endpoint, service, or file path.
- Expected impact.
- Any safe logs or screenshots with secrets removed.

## Local Secret Handling

- Keep `.env` local. It is ignored by Git.
- Use `.env.example` only as a template.
- Rotate `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD`, and `INTERNAL_SECRET_KEY` before deployment.
- Do not commit runtime uploads from `backend/uploads/`.
- Do not commit generated local caches such as `.venv/`, `node_modules/`, `frontend/dist/`, coverage reports, or Playwright reports.
