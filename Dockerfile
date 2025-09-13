FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy source code first (controlled by .dockerignore)
COPY . .

# Install the package
RUN pip install -e .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "interface.main:app", "--host", "0.0.0.0", "--port", "8000"]
