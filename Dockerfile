FROM python:3.11.9

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user and set permissions
RUN adduser --disabled-password --gecos "" app && \
    touch /app/app.log && \
    chown app:app /app/app.log && \
    chmod 644 /app/app.log

USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Start the FastAPI app using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
