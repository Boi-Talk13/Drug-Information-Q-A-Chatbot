# MedCite — one image that builds the React frontend and serves it from the
# FastAPI backend, so http://localhost:8000 gives the whole app.

# ---- stage 1: build the frontend ------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: the python backend ------------------------------------------
FROM python:3.12-slim AS app
WORKDIR /app

# System deps kept minimal; PyMuPDF ships wheels so no compiler is needed.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY data/ data/
# Bring in the built frontend so the API can serve it on the same port.
COPY --from=frontend /app/frontend/dist frontend/dist

EXPOSE 8000
# Build the index on start (if PDFs are present), then serve.
CMD ["sh", "-c", "python -m backend.build_index || true; uvicorn backend.api.main:app --host 0.0.0.0 --port 8000"]
