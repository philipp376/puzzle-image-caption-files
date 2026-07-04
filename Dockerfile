FROM python:3.11-slim

WORKDIR /app

# fonts-dejavu-core provides the bold TTF font used for the caption overlay.
# libgl1 / libglib2.0-0 are common runtime deps for opencv-python-headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
