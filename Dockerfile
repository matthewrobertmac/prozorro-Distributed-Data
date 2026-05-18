FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY live_dashboard/frontend/package*.json ./
RUN npm install
COPY live_dashboard/frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 && rm -rf /var/lib/apt/lists/*

COPY live_dashboard/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY live_dashboard/backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Create a fake dotenv to prevent backend error
RUN touch .env

EXPOSE 8080
ENV PORT=8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
