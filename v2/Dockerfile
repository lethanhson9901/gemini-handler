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

CMD ["python", "-m", "main", "--host", "0.0.0.0", "--port", "8000"]