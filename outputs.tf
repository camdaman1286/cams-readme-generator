# --- Bucket ---
output "readme_bucket_name" {
  description = "The name of the S3 bucket where README files are stored."
  value       = module.s3_bucket.bucket_id
}

# --- Agent IDs ---
output "repo_scanner_agent_id" {
  description = "The ID of the Repo Scanner Agent."
  value       = module.repo_scanner_agent.agent_id
}

output "project_summarizer_agent_id" {
  description = "The ID of the Project Summarizer Agent."
  value       = module.project_summarizer_agent.agent_id
}

output "installation_guide_agent_id" {
  description = "The ID of the Installation Guide Agent."
  value       = module.installation_guide_agent.agent_id
}

output "usage_examples_agent_id" {
  description = "The ID of the Usage Examples Agent."
  value       = module.usage_examples_agent.agent_id
}

output "final_compiler_agent_id" {
  description = "The ID of the Final Compiler Agent."
  value       = module.final_compiler_agent.agent_id
}