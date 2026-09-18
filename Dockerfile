FROM python:3.13-slim

WORKDIR /app

COPY backend /app/backend
COPY frontend /app/frontend

ENV PYTHONUNBUFFERED=1
ENV WMS_DATA_DIR=/data

EXPOSE 8000

CMD ["python3","-m","backend.wms_web.app","--host","0.0.0.0","--port","8000"]
