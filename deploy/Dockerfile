FROM python:3.12-slim
 
# Set working directory
WORKDIR /app
 
# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
 
# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir \
    google-cloud-bigquery[pandas] \
    google-cloud-bigquery-storage \
    pyarrow \
    db-dtypes \
    langchain \
    langchain-google-genai \
    langgraph \
    streamlit \
    joblib \
    pandas \
    scikit-learn \
    xgboost \
    shap \
    python-dotenv

# Copy app files
COPY agent/app.py .
COPY fraud_model.pkl .
COPY model_metadata.pkl .
COPY shap_values_sample.csv .

RUN mkdir -p /root/.streamlit
RUN echo '\
[server]\n\
headless = true\n\
port = 8080\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
' > /root/.streamlit/config.toml

# Cloud Run uses port 8080
EXPOSE 8080
 
# Run the app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]