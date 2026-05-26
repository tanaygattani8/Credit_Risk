import os
import subprocess
import sys

# Config
PROJECT_ID   = os.environ.get("GCP_PROJECT_ID", "finance-497101")
REGION       = "us-central1"
SERVICE_NAME = "fraud-investigation-agent"
IMAGE_NAME   = f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}"

def run(cmd: str, check: bool = True) -> None:
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, check=check)
    return result

def main():
    print("Phase 5: Deploy to Cloud Run")
    print(f"   Project : {PROJECT_ID}")
    print(f"   Region  : {REGION}")
    print(f"   Service : {SERVICE_NAME}")

    # 1. Enable required APIs
    print("\n── Step 1: Enable APIs")
    run(f"gcloud services enable cloudbuild.googleapis.com run.googleapis.com --project={PROJECT_ID}")

    # 2. Build and push Docker image via Cloud Build (no local Docker needed)
    print("\n── Step 2: Build Docker image with Cloud Build")
    print("   (This uses Cloud Build — no Docker Desktop required on Windows)")
    run(f"gcloud builds submit --tag {IMAGE_NAME} --project={PROJECT_ID} .")

    # 3. Deploy to Cloud Run
    print("\n── Step 3: Deploy to Cloud Run")
    run(f"""gcloud run deploy {SERVICE_NAME} \
        --image {IMAGE_NAME} \
        --platform managed \
        --region {REGION} \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 1 \
        --timeout 300 \
        --set-env-vars GCP_PROJECT_ID={PROJECT_ID} \
        --set-env-vars GOOGLE_AI_API_KEY={os.environ.get('GOOGLE_AI_API_KEY', '')} \
        --project={PROJECT_ID}""")

    # 4. Get the live URL
    print("\n── Step 4: Get service URL")
    result = subprocess.run(
        f"gcloud run services describe {SERVICE_NAME} --region={REGION} --format='value(status.url)' --project={PROJECT_ID}",
        shell=True, capture_output=True, text=True
    )
    url = result.stdout.strip()
    print(f"\n  ✓ Your app is live at: {url}")
    print(f"  ✓ Add this URL to your resume and GitHub README")
    print("\n── Deployment complete.")

if __name__ == "__main__":
    main()
