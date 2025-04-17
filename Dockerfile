# Use a specific version of the Python slim image
FROM python:3.12-slim AS base

# Set environment variables for non-interactive installs
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Path where uv installs packages when using --system
    PYTHONPATH=/usr/local/lib/python3.12/site-packages

# --- Security: Create a non-root user and group ---
ARG UID=1001
ARG GID=1001
RUN groupadd -g $GID appgroup && \
    useradd -u $UID -g $GID -m -s /sbin/nologin appuser

# --- Install uv ---
# Using pip to install uv initially
RUN pip install uv

WORKDIR /app

# --- Install Dependencies ---
# Copy only the dependency definition file(s) first to leverage caching
# Adjust this line if you use requirements.txt or have lock files
# COPY pyproject.toml ./
COPY requirements.txt config.yaml ./
# COPY uv.lock ./        # Uncomment if you use a uv lock file

# Install dependencies using uv
# Use 'uv pip sync' if pyproject.toml defines all dependencies (incl. transitive)
# Or 'uv pip install -r requirements.txt' if using requirements.txt
# --system installs into the global site-packages
# --no-cache prevents caching within the RUN command (PIP_NO_CACHE_DIR handles pip's cache)
# RUN uv pip sync --system --no-cache pyproject.toml
RUN uv pip install --system --no-cache -r requirements.txt 

# --- Copy Application Code ---
# Copy the rest of the application code
COPY . .

# --- Final Setup ---
# Change ownership to the non-root user
# Ensure the WORKDIR exists and change ownership
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# --- Runtime Command ---
# How to run the application
# Using python -m assumes your cli module is runnable this way
CMD ["python", "-m", "gemini_handler.cli"]

# --- IMPORTANT: API Key Handling ---
# DO NOT set API keys using ENV in the Dockerfile.
# Pass them securely at runtime, for example:
#
# Using docker run:
# docker run -p 8000:8000 \
#   -e GEMINI_API_KEY="your_actual_key" \
#   -e GEMINI_API_KEYS="key1,key2" \
#   your_image_name
#
# Using Docker Compose (docker-compose.yml):
# services:
#   myapp:
#     image: your_image_name
#     ports:
#       - "8000:8000"
#     environment:
#       GEMINI_API_KEY: ${GEMINI_API_KEY_FROM_HOST_OR_ENV_FILE}
#       GEMINI_API_KEYS: ${GEMINI_API_KEYS_FROM_HOST_OR_ENV_FILE}
#
# Or using secrets management systems like Docker Secrets, Kubernetes Secrets, etc.