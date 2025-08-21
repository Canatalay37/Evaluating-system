# Use Python 3.9 (should be available without auth)
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc g++ musl-dev

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
CMD ["python", "gui_evaluating.py"]
