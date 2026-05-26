import os
import subprocess

PROJECT_ID   = os.environ.get("GCP_PROJECT_ID")
REGION       = "us-central1"
FUNCTION_NAME = "fraud-dbt-refresh"
SCHEDULER_JOB = "daily-fraud-pipeline"

# Cloud Function source code (inline) 
FUNCTION_CODE = '''
import subprocess
import functions_framework

@functions_framework.http
def run_dbt(request):
    """HTTP Cloud Function that triggers dbt run."""
    try:
        result = subprocess.run(
            ["dbt", "run", "--project-dir", "/workspace/Credit_Risk",
             "--profiles-dir", "/workspace"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return f"DBT run succeeded:\\n{result.stdout}", 200
        else:
            return f"DBT run failed:\\n{result.stderr}", 500
    except Exception as e:
        return f"Error: {str(e)}", 500
'''

REQUIREMENTS = '''
functions-framework==3.8.1
dbt-bigquery==1.8.2
'''

def run(cmd: str) -> None:
    print(f"\n$ {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def main():
    print("Phase 5: Automated Pipeline Setup")

    # Write Cloud Function files
    import tempfile, os
    tmpdir = tempfile.mkdtemp()

    with open(os.path.join(tmpdir, "main.py"), "w") as f:
        f.write(FUNCTION_CODE)
    with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
        f.write(REQUIREMENTS)

    print(f"\n── Step 1: Deploy Cloud Function from {tmpdir}")
    run(f"""gcloud functions deploy {FUNCTION_NAME} \
        --gen2 \
        --runtime=python312 \
        --region={REGION} \
        --source={tmpdir} \
        --entry-point=run_dbt \
        --trigger-http \
        --allow-unauthenticated \
        --memory=512MB \
        --timeout=300s \
        --project={PROJECT_ID}""")

    # Get function URL
    result = subprocess.run(
        f"gcloud functions describe {FUNCTION_NAME} --region={REGION} --format='value(serviceConfig.uri)' --project={PROJECT_ID}",
        shell=True, capture_output=True, text=True
    )
    function_url = result.stdout.strip()
    print(f"  ✓ Function URL: {function_url}")

    # Create Cloud Scheduler job — runs at 6am UTC daily
    print("\n── Step 2: Create Cloud Scheduler job (6am UTC daily)")
    run(f"""gcloud scheduler jobs create http {SCHEDULER_JOB} \
        --location={REGION} \
        --schedule="0 6 * * *" \
        --uri="{function_url}" \
        --http-method=GET \
        --project={PROJECT_ID}""")

    print(f"\n  ✓ Pipeline will auto-refresh every day at 6am UTC")
    print(f"  ✓ Check logs: https://console.cloud.google.com/functions/details/{REGION}/{FUNCTION_NAME}")
    print("\n── Automation setup complete.")

if __name__ == "__main__":
    main()
