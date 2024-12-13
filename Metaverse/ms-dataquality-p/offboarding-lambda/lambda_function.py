import boto3
import os
import subprocess
import json
import logging

s3 = boto3.client('s3')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TERRAFORM_SCRIPT_BUCKET = "offboard-buck"
TERRAFORM_SCRIPT_KEY = "offboarding.tf"

def download_file_from_s3(bucket, key, local_path):
    try:
        s3.download_file(bucket, key, local_path)
        logger.info(f"Successfully downloaded {key} from {bucket}")
    except Exception as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        raise

def write_terraform_vars(variables, file_path):
    with open(file_path, 'w') as f:
        for key, value in variables.items():
            f.write(f'{key} = "{value}"\n')
    logger.info(f"Terraform variables written to {file_path}")

def run_terraform_command(command, cwd):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        logger.error(f"Terraform command failed: {stderr.decode()}")
        raise Exception(f"Terraform command failed: {stderr.decode()}")
    return stdout.decode()

def lambda_handler(event, context):
    try:
        logger.info("Starting offboarding process")
        logger.info(f"Event: {json.dumps(event)}")

        user_id = event['user_id']
        instance_id = event['instance_id']
        instance_type = event['instance_type']
        aws_account_id = event['aws_account_id']
        aws_access_key_id = event['aws_access_key_id']
        aws_secret_access_key = event['aws_secret_access_key']

        # Write Terraform variables to a file
        variables = {
            'user_id': user_id,
            'instance_id': instance_id,
            'instance_type': instance_type,
            'aws_account_id': aws_account_id,
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'aws_region': os.environ['AWS_DEFAULT_REGION']
        }
        write_terraform_vars(variables, '/tmp/terraform.tfvars')

        # Download Terraform script from S3
        download_file_from_s3(TERRAFORM_SCRIPT_BUCKET, TERRAFORM_SCRIPT_KEY, '/tmp/offboarding.tf')

        # Run Terraform init
        logger.info("Initializing Terraform")
        init_output = run_terraform_command('terraform init', '/tmp')
        logger.info(f"Terraform init output: {init_output}")

        # Run Terraform apply
        logger.info("Applying Terraform changes")
        apply_output = run_terraform_command('terraform apply -auto-approve -var-file=terraform.tfvars', '/tmp')
        logger.info(f"Terraform apply output: {apply_output}")

        # Parse the output to get information about deleted resources
        deleted_resources = parse_terraform_output(apply_output)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Offboarding completed successfully',
                'deleted_resources': deleted_resources
            })
        }
    except Exception as e:
        logger.error(f"Error in offboarding process: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Offboarding failed',
                'error': str(e)
            })
        }

def parse_terraform_output(output):
    # This is a simple parser and might need to be adjusted based on your actual Terraform output
    deleted_resources = {}
    lines = output.split('\n')
    for line in lines:
        if 'Destroy complete!' in line:
            deleted_resources['status'] = 'All resources destroyed'
        elif 'Destroying...' in line:
            resource = line.split('Destroying...')[1].strip()
            deleted_resources[resource] = 'Destroyed'
    return deleted_resources