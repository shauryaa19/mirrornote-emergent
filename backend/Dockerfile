FROM python:3.12-slim

# Install uv and other dependencies
RUN apt-get update && apt-get install -y gcc g++ build-essential

RUN pip install uv

# Set workdir
WORKDIR /app

# Copy project
COPY . .

# Install backend deps
RUN uv pip install -r requirements.txt --system

# Expose port
EXPOSE 8000

# Run server
CMD ["sh", "-c", "cd backend && uv run uvicorn server:app --host 0.0.0.0 --port $PORT"]
