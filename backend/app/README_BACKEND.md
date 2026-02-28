This folder contains the FastAPI backend for Aadya - Nexora AI.

Endpoints:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/chat/stream (requires Bearer token) - streams SSE
- POST /api/admin/ingest - ingest texts (admin)

Environment variables are read from `.env` in the root.
