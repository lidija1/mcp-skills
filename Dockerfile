FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (if not already in base image or to ensure they're up to date)
RUN playwright install --with-deps

# Copy the rest of the application
COPY . .

# Create necessary directories for reports and logs
RUN mkdir -p reports logs screenshots allure-results

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Run pytest with appropriate flags
# Note: Headless mode is controlled in conftest.py or test code, not here
# Supports running validation tests in parallel with load scheduling
# Usage: docker run --rm playwright-tests:latest pytest -m validation -n 4 -v
CMD ["pytest", "--html=reports/report.html", "--self-contained-html", "--alluredir=allure-results", "-v"]
