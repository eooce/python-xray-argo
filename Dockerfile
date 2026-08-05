FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        openssl \
        ca-certificates \
        libc6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py index.html /tmp

EXPOSE tcp/3000

CMD ["python3", "app.py"]
