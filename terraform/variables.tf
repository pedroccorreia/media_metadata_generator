variable "project_id" {
  description = "The Google Cloud project ID to deploy the resources in."
  type        = string # set in .tfvars
}

variable "region" {
  description = "The Google Cloud region to deploy the resources in."
  type        = string
  default     = "us-central1"
}

variable "input_bucket_names" {
  description = "A list of Google Cloud Storage bucket names to be created for media input."
  type        = set(string)
  default     = []
}

variable "output_bucket_name" {
  description = "The Google Cloud Storage bucket name for output files."
  type        = string
  default     = "output-bucket"
}

variable "artifact_registry_repo" {
  description = "The name of the Artifact Registry repository to store Docker images."
  type        = string
  default     = "media-pipeline-images"
}

# Docker Images for Cloud Run Services
variable "batch_processor_image" {
  description = "Docker image URL for the Batch Processor Cloud Run service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "summaries_generator_image" {
  description = "Docker image URL for the Summaries Generator Cloud Run service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "transcription_generator_image" {
  description = "Docker image URL for the Transcription Generator Cloud Run service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "previews_generator_image" {
  description = "Docker image URL for the Previews Generator Cloud Run service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "nebula_foundry_ui_image" {
  description = "Docker image URL for the Nebula Foundry UI Cloud Run service."
  type = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "nebula_foundry_ui_backend_image" {
  description = "Docker image URL for the Nebula Foundry UI Backend Cloud Run service."
  type = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "summaries_generator_llm_model" {
  description = "The LLM model to be used by the summaries generator service."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "transcription_generator_llm_model" {
  description = "The LLM model to be used by the transcription generator service."
  type        = string
  default     = "chirp"
}

variable "previews_generator_llm_model" {
  description = "The LLM model to be used by the previews generator service."
  type        = string
  default     = "gemini-2.5-flash"
}



# Concurrency threshold for dispatcher and metadata generator services
variable "batch_processor_concurrency" {
  description = "The maximum number of concurrent requests for the Batch Processor service."
  type        = number
  default     = 80
}

variable "summaries_generator_concurrency" {
  description = "The maximum number of concurrent requests for the Summaries Generator service."
  type        = number
  default     = 80
}

variable "transcription_generator_concurrency" {
  description = "The maximum number of concurrent requests for the Transcription Generator service."
  type        = number
  default     = 1
}

variable "previews_generator_concurrency" {
  description = "The maximum number of concurrent requests for the Previews Generator service."
  type        = number
  default     = 80
}
