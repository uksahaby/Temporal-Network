# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements first for better caching
COPY requirement.txt .

# Install Python dependencies using pre-built binary wheels only.
# leidenalg, igraph, and psycopg2-binary all ship manylinux wheels for
# Python 3.12 / linux-x86_64, so no compiler or system packages are needed.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirement.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads data/processed data/cache

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
