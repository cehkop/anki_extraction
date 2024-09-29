####################################################
# Stage 1: Build stage for installing dependencies #
####################################################
FROM python:3.11-slim-bookworm AS builder

RUN mkdir /svc
WORKDIR /svc
COPY requirements.lock .

# Upgrade pip and build wheels
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel -r requirements.lock --wheel-dir=/svc/wheels

###########################################################
# Stage 2: Final stage with Selenium and application code #
###########################################################
FROM python:3.11-slim-bookworm
USER root

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python and dependencies
RUN apt-get update && apt-get install -yq --no-install-recommends \
    # supervisor curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /svc /svc

# Install Python packages from wheels
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --no-deps --find-links=/svc/wheels -r /svc/requirements.lock

# Set working directory
WORKDIR /app

# Copy the application code
COPY src /app/src
COPY .env /app/.env

# Create a non-root user and make directories for logs with appropriate permissions
RUN useradd -m app \
    && mkdir -p /app/logs /var/log/supervisor \
    && chown -R app:app /app/logs /var/log/supervisor /app \
    && chmod -R 0777 /app/logs /app /var/log/supervisor

# Switch to non-root user
USER app

# Expose the port
EXPOSE 2341

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2341"]