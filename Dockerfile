FROM python:3.11-slim

WORKDIR /JuukBoxDiscordBot

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libffi-dev \
    libsodium-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV SODIUM_INSTALL=system
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]

