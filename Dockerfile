# ------------------------------------------------------------------------
# Project: TS_XL_Modifier
# Author:  Karl @ TechnoShed
# Repo:    https://github.com/TechnoShed-dev/TS_XL_Modifier
# ------------------------------------------------------------------------

FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit on default port 8501
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]