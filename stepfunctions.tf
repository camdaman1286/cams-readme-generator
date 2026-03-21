# IAM role for Step Functions to invoke Lambda functions
resource "aws_iam_role" "step_functions_role" {
  name = "cams-ReadmeGeneratorStepFunctionsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
}

# Allows Step Functions to invoke all pipeline Lambdas
resource "aws_iam_policy" "step_functions_policy" {
  name = "cams-ReadmeGeneratorStepFunctionsPolicy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InvokePipelineLambdas"
      Effect = "Allow"
      Action = "lambda:InvokeFunction"
      Resource = [
        aws_lambda_function.invoke_repo_scanner.arn,
        aws_lambda_function.invoke_summarizer.arn,
        aws_lambda_function.invoke_installation.arn,
        aws_lambda_function.invoke_usage.arn,
        aws_lambda_function.invoke_compiler.arn
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "step_functions_policy_attach" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.step_functions_policy.arn
}

# Step Functions state machine definition
resource "aws_sfn_state_machine" "readme_pipeline" {
  name     = "cams-ReadmeGeneratorPipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    Comment = "README Generator pipeline - runs analytical agents in parallel"
    StartAt = "ScanRepo"

    States = {
      # Step 1: Scan the repo to get the file list
      ScanRepo = {
        Type     = "Task"
        Resource = aws_lambda_function.invoke_repo_scanner.arn
        Retry = [{
          ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "EventStreamError"]
          IntervalSeconds = 5
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Next = "CheckScanResult"
      }

      # Step 2: Guard - check if scan returned files
      CheckScanResult = {
        Type    = "Choice"
        Choices = [{
          Variable      = "$.file_list"
          StringMatches = "*files*"
          Next          = "WaitBeforeParallel"
        }]
        Default = "RepoNotFound"
      }

      # Step 2b: Wait to avoid Bedrock throttling before firing parallel calls
      WaitBeforeParallel = {
        Type    = "Wait"
        Seconds = 10
        Next    = "AnalyzeInParallel"
      }

      # Step 3: Run analytical agents in parallel with retries for throttling
      AnalyzeInParallel = {
        Type = "Parallel"
        Branches = [
          {
            StartAt = "InvokeSummarizer"
            States = {
              InvokeSummarizer = {
                Type     = "Task"
                Resource = aws_lambda_function.invoke_summarizer.arn
                Retry = [{
                  ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "EventStreamError"]
                  IntervalSeconds = 15
                  MaxAttempts     = 5
                  BackoffRate     = 2
                }]
                End = true
              }
            }
          },
          {
            StartAt = "InvokeInstallation"
            States = {
              InvokeInstallation = {
                Type     = "Task"
                Resource = aws_lambda_function.invoke_installation.arn
                Retry = [{
                  ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "EventStreamError"]
                  IntervalSeconds = 15
                  MaxAttempts     = 5
                  BackoffRate     = 2
                }]
                End = true
              }
            }
          },
          {
            StartAt = "InvokeUsage"
            States = {
              InvokeUsage = {
                Type     = "Task"
                Resource = aws_lambda_function.invoke_usage.arn
                Retry = [{
                  ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "EventStreamError"]
                  IntervalSeconds = 15
                  MaxAttempts     = 5
                  BackoffRate     = 2
                }]
                End = true
              }
            }
          }
        ]
        Next = "MergeAndCompile"
      }

      # Step 4: Merge parallel results and compile the README
      MergeAndCompile = {
        Type     = "Task"
        Resource = aws_lambda_function.invoke_compiler.arn
        Retry = [{
          ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "EventStreamError"]
          IntervalSeconds = 15
          MaxAttempts     = 5
          BackoffRate     = 2
        }]
        Parameters = {
          "repo_name.$"          = "$$.Execution.Input.repo_name"
          "session_id.$"         = "$$.Execution.Input.session_id"
          "output_key.$"         = "$$.Execution.Input.output_key"
          "feedback_key.$"       = "$$.Execution.Input.feedback_key"
          "project_summary.$"    = "$[0].project_summary"
          "installation_guide.$" = "$[1].installation_guide"
          "usage_examples.$"     = "$[2].usage_examples"
        }
        End = true
      }

      # Fallback state when repo scan returns no files
      RepoNotFound = {
        Type  = "Fail"
        Error = "RepoNotFound"
        Cause = "The repository could not be scanned. It may be private, empty, or the URL is invalid."
      }
    }
  })
}

output "state_machine_arn" {
  description = "The ARN of the Step Functions state machine."
  value       = aws_sfn_state_machine.readme_pipeline.arn
}
