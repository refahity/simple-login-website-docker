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
ENV APP_ENV=production 

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies and create a non-root user
RUN pip3 install --no-cache-dir -r requirements.txt \
    && adduser --disabled-password --gecos "" appuser

# Copy the application code into the container
COPY app.py .

# Switch to the non-root user for security
USER appuser

# Expose the application port
EXPOSE 5001

# Define the command to run the application
CMD ["python3", "app.py"]

