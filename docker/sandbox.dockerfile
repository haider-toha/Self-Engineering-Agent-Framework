FROM python:3.10-slim

# Install common packages for data processing and testing
RUN pip install --no-cache-dir pytest pandas numpy openpyxl xlrd

# Set working directory
WORKDIR /code

# Default command (will be overridden)
CMD ["pytest"]

