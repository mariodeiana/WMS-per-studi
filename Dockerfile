FROM node:20-bookworm-slim AS angular-build
WORKDIR /build
COPY frontend-angular/package.json frontend-angular/package-lock.json ./
RUN npm ci
COPY frontend-angular/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY backend /app/backend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY frontend /app/frontend
COPY --from=angular-build /build/dist/frontend-angular/browser /app/frontend-angular/dist/frontend-angular/browser
ENV PYTHONUNBUFFERED=1
ENV WMS_DATA_DIR=/data
ENV WMS_FRONTEND=angular
EXPOSE 8000
CMD ["python3","-m","backend.wms_web.app","--host","0.0.0.0","--port","8000"]
