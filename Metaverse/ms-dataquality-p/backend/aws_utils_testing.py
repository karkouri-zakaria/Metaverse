import boto3
import json
import logging
import os
from dotenv import load_dotenv

env_file = '.env'
load_dotenv(env_file, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSUtils:
    def __init__(self):
        self.lambda_client = boto3.client('lambda',
                                          region_name=os.getenv('AWS_REGION'),
                                          aws_access_key_id=os.getenv('ACCESS_KEY'),
                                          aws_secret_access_key=os.getenv('SECRET_KEY'))


    def invoke_lambda(self, function_name, payload):
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_payload = json.loads(response['Payload'].read())
            return response_payload
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {str(e)}")
            raise







