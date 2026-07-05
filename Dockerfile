FROM python:3.12-slim

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 18080

CMD ["python", "/app/app.py", "--host", "0.0.0.0", "--port", "18080", "--state", "/data/state.json"]
