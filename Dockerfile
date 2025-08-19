# Start from a minimal base operating system instead of a prebuilt Python image (last version)
FROM debian:stable-slim

# Set working directory inside the container
WORKDIR /app

# Install Python and required tools (pip, venv, etc.)
# -y automatically answers "yes" to apt prompts
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables 
# APP_ENV: tells the app in which environment it's running (dev/prod)
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

#  create a non-root user
RUN useradd -m appuser

# Copy the application code into the container
COPY app.py .

# Set environment variables for security used in programe code
ENV  APP_PORT=5000

# Switch to the non-root user for security
USER appuser

# Expose the application port
EXPOSE ${APP_PORT}

# Define the command to run the application
CMD ["python3", "app.py"]


