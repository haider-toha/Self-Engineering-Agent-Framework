FROM python:3.10-slim

# Install pytest
RUN pip install --no-cache-dir pytest

# Set working directory
WORKDIR /code

# Default command (will be overridden)
CMD ["pytest"]

