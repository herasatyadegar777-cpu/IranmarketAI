FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/main.py ./main.py
ENV PORT=8000
ENV ENABLE_REAL_DATA=1
ENV ALLOW_DEMO_FALLBACK=0
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

ENV ENABLE_POLLING=1
ENV POLL_SECONDS=60
