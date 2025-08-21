# Use Ubuntu base image (more commonly available)
FROM ubuntu:20.04

# Set working directory
WORKDIR /app

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory for database
RUN mkdir -p instance

# Expose port
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=gui_evaluating.py
ENV FLASK_ENV=production

# Run the application
CMD ["python3", "gui_evaluating.py"]
