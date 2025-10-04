# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

# install Python deps first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source (root files + app package)
COPY main.py pyproject.toml README.md uv.lock ./
COPY app ./app

# expose your FastAPI port
EXPOSE 7004

# run your entrypoint
CMD ["python", "main.py"]
