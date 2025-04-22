# Dockerfile with multi-stage build for both CPU and GPU support
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 as gpu
FROM python:3.9-slim as cpu

# Create final stage based on build arg
ARG DEVICE=cpu
FROM ${DEVICE}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install torch with appropriate backend
RUN if [ "${DEVICE}" = "gpu" ] ; then \
        pip install --no-cache-dir torch==2.0.0+cu118 -f https://download.pytorch.org/whl/torch_stable.html ; \
    else \
        pip install --no-cache-dir torch==2.0.0 -f https://download.pytorch.org/whl/cpu/torch_stable.html ; \
    fi

RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Create directories for uploads and vector indices
RUN mkdir -p uploads vector_indices

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]