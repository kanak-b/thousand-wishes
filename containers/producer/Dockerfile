# Use a lightweight Python image
FROM python:3.9-slim AS builder

# Set working directory
WORKDIR /app

# Install dependencies separately to leverage caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy only necessary files
COPY producer.py .

# Set environment variable for Kafka broker
ENV KAFKA_BROKER=kafka:9092

# Command to run the script
CMD ["python", "producer.py"]
