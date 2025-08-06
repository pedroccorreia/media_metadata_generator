gcloud artifacts repositories create my-repo --repository-format=docker --location=asia-southeast1 --description="Docker repository for metadata pipeline images"
docker build -t asia-southeast1-docker.pkg.dev/your-gcp-project-id/my-repo/summaries-generator:latest /path/to/your/summaries_generator_code
docker push asia-southeast1-docker.pkg.dev/your-gcp-project-id/my-repo/summaries-generator:latest