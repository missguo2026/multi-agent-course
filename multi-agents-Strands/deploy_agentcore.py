import os
import time
from pathlib import Path

from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session


os.chdir(Path(__file__).resolve().parent)

region = Session().region_name or "us-west-2"

s3_bucket = os.environ["S3_BUCKET"]

agentcore_runtime = Runtime()

agentcore_runtime.configure(
    entrypoint="travel_assistant.py",
    auto_create_execution_role=True,
    auto_create_s3=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name="travel_assistant",
    deployment_type="direct_code_deploy",
    runtime_type="PYTHON_3_12",
)

launch_result = agentcore_runtime.launch(
    auto_update_on_conflict=True,
    env_vars={"S3_BUCKET": s3_bucket},
)

status_response = agentcore_runtime.status()

status = status_response.endpoint["status"]

finished_statuses = {
    "READY",
    "CREATE_FAILED",
    "DELETE_FAILED",
    "UPDATE_FAILED",
}

while status not in finished_statuses:
    time.sleep(10)

    status_response = agentcore_runtime.status()

    status = status_response.endpoint["status"]

    print(status)

if status != "READY":
    raise RuntimeError(f"AgentCore deployment finished with status: {status}")

print(f"Agent ARN: {launch_result.agent_arn}")
