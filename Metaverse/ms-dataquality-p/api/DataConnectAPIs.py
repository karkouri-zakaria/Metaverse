import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.dataconnect import DataconnectBackend
from backend.gitlab_utils import GitLabUtils
from backend.database import Database
from dotenv import load_dotenv
import logging
import time
from pydantic import BaseModel
from typing import List
from typing import List, Optional

# Load environment variables
env_file = '.env'
load_dotenv(env_file, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for all routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_name = os.getenv('DB_NAME')
db = Database()
dcb = DataconnectBackend()
gl_utils = GitLabUtils()



class DatasetCreate(BaseModel):
    name: str
    connexion_status: Optional[str] = None
    dataset_type: Optional[str] = None
    last_scan: Optional[str] = None
    column_delimiter: Optional[str] = None
    excape_char: Optional[str] = None

class DatasourceCreate(BaseModel):
    name: str
    datasets: List[DatasetCreate]

class DataconnectCreate(BaseModel):
    user_id: str
    user_id_variable: str
    instance_id: str
    instance_type: str
    workspace_id: str
    region: Optional[str] = None
    key: Optional[str] = None  
    aws_secret_access_key: Optional[str] = None
    drive_client_secret: Optional[str] = None
    drive_client_id: Optional[str] = None
    drive_refresh_token: Optional[str] = None
    datasources: List[DatasourceCreate] = None

class DataconnectDelete(BaseModel):
    USER_ID: str
    INSTANCE_ID: str
    INSTANCE_TYPE: str

class DataconnectFiles(BaseModel):
    user_id: str
    instance_id: str
    instance_type: str
    source_name: str


@app.post("/api/data-connect/create/get-buckets-folders")
async def get_buckets_folders(dataconnect: DataconnectCreate):
    try:
        # Step 1: Check Lambda function existence
        if not await dcb.check_lambda_existence(dataconnect):
            # Deploy required resources
            pipeline = await deploy_resources(dataconnect)
            # Wait for pipeline completion
            if not await wait_for_pipeline(pipeline.id):
                raise HTTPException(status_code=500, detail="Pipeline deployment failed")

        # Step 2: Fetch data based on instance type
        return await fetch_instance_data(dataconnect)

    except Exception as e:
        logger.error(f"Error in get_buckets_folders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def deploy_resources(dataconnect):
    """Deploys resources by triggering a pipeline based on the instance type."""
    variables = [
        {'key': 'USER_ID', 'value': dataconnect.user_id},
        {'key': 'INSTANCE_ID', 'value': dataconnect.instance_id},
        {'key': 'INSTANCE_TYPE', 'value': dataconnect.instance_type}
    ]
    
    if dataconnect.instance_type == 's3':
        variables.extend([
            {'key': 'REGION', 'value': dataconnect.region},
            {'key': 'KEY', 'value': dataconnect.key},
            {'key': 'SECRET_KEY', 'value': dataconnect.aws_secret_access_key}
        ])
    elif dataconnect.instance_type == 'Google_Drive':
        variables.extend([
            {'key': 'CLIENT_SECRET', 'value': dataconnect.drive_client_secret},
            {'key': 'CLIENT_ID', 'value': dataconnect.drive_client_id},
            {'key': 'REFRESH_TOKEN', 'value': dataconnect.drive_refresh_token}
        ])

    pipeline = await gl_utils.trigger_pipeline(variables=variables)
    return pipeline

async def wait_for_pipeline(pipeline_id: str) -> bool:
    """Checks the pipeline status until completion or failure."""
    while True:
        status = await gl_utils.check_pipeline_status(pipeline_id)
        if status in ['success', 'failed']:
            break
    return status == 'success'

async def fetch_instance_data(dataconnect):
    """Fetches buckets or folders based on instance type."""
    if dataconnect.instance_type == 's3':
        buckets, error = await dcb.get_buckets(dataconnect)
        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch S3 buckets")
        return {
            "buckets": [
                {key: value for key, value in bucket.items()} for bucket in buckets
            ]
        }
    elif dataconnect.instance_type == 'google_drive':
        folders, error = await dcb.get_google_drive_folders(dataconnect)
        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch Google Drive folders")
        return {
            "folders": [
                {key: value for key, value in folder.items()} for folder in folders
            ]
        }


    
@app.post("/api/data-connect/files")
async def get_files(dataconnect: DataconnectFiles):
    try:
        if dataconnect.instance_type == 's3':
            files, error = await dcb.get_bucket_files(dataconnect, dataconnect.source_name)
        elif dataconnect.instance_type == 'google_drive':
            files, error = await dcb.get_google_drive_files(dataconnect, dataconnect.source_name)

        if error:
            raise HTTPException(status_code=500, detail="Failed to retrieve files")
        return files
    except Exception as e:
        logger.error(f"Error in get_files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch datastes")
    

    
@app.post("/api/data-connect/create-instance")
async def create_datacon_instance(dataconnect: DataconnectCreate):
    try:
        variables = [
            {'key': 'user_id', 'value': dataconnect.user_id},
            {'key': 'user_id_variable', 'value': dataconnect.user_id_variable},
            {'key': 'instance_type', 'value': dataconnect.instance_type},
            {'key': 'instance_id', 'value': dataconnect.instance_id},
            {'key': 'workspace_id', 'value': dataconnect.workspace_id}
        ] 

        if dataconnect.instance_type == 's3':
            variables.extend([
                {'key': 'region', 'value': dataconnect.region},
                {'key': 'key', 'value': dataconnect.key},
                {'key': 'secret_key', 'value': dataconnect.aws_secret_access_key}
                ])
        elif dataconnect.instance_type == 'google_drive':
            variables.extend([
                {'key': 'client_secret', 'value': dataconnect.drive_client_secret},
                {'key': 'client_id', 'value': dataconnect.drive_client_id},
                {'key': 'refresh_token', 'value': dataconnect.drive_refresh_token},
            ])

        db.insert_dataconnect(dataconnect)

        for datasource in dataconnect.datasources:
            source_id = db.insert_datasource(datasource, dataconnect.instance_id)
            for dataset in datasource.datasets:
                db.insert_dataset(dataset, source_id)

        return {
            "message": "Dataconnect instance created successfully.",
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/data-connect/instances/{user_id}/{workspace_id}")
async def get_users_datacon_insts(user_id: str, workspace_id: str):
    try:
        # Call the controller function that will use the DB function to get the dataconnect instances
        datacons = dcb.get_user_dataconnects(user_id, workspace_id)

        # Return the datacon instances
        return datacons

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# This endpoint I placed here to maintain the order of APIs as specified in the README file.
@app.get("/api/data-connect/get-sources/{instance_id}")
async def get_instance_buckets_folders(instance_id: str):
    try:
        datasrcs = db.get_instance_sources(instance_id)
        return datasrcs
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.delete("/api/data-connect/delete")
async def offboard_instance(creds: dict, resources: dict):
    try:
        # Step 1: Delete AWS resources
        response = delete_aws_resources(creds, resources)
        # Step 2: Delete associated database records if AWS deletion is successful
        if response and response["status"] == "success":
            db.delete_dataconnect_and_related_records(resources["id"])
        
        return response

    except HTTPException as e:
        # Raise FastAPI exception
        raise e

    except Exception as e:
        # Catch any unexpected exceptions
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# Function to delete resources
def delete_aws_resources(creds, resources):
    try:
        session = boto3.Session(
            aws_access_key_id=creds["aws_access_key_id"],
            aws_secret_access_key=creds["aws_secret_access_key"],
            region_name=creds["region"]
        )
        
        lambda_client = session.client('lambda')
        secrets_client = session.client('secretsmanager')
        kms_client = session.client('kms')
        ecr_client = session.client('ecr')

        # Delete Lambda function
        lambda_client.delete_function(FunctionName=f"{resources['instance_id']}_s3_lambda")
        print(f"Deleted Lambda function: {resources['instance_id']}_s3_lambda")

                # Delete Secrets Manager record
        secrets_client.delete_secret(SecretId=f"{resources['user_id']}_{resources['instance_id']}_s3_secrets", ForceDeleteWithoutRecovery=True)
        print(f"Deleted secret: {resources['user_id']}_{resources['instance_id']}_s3_secrets")

        # Schedule KMS key deletion
        alias_name = f"{resources['user_id']}_{resources['instance_id']}_s3_kms_key"
        alias_response = kms_client.list_aliases()
        kms_key_id = None

        # Find the KMS key ID for the alias
        for alias in alias_response.get("Aliases", []):
            if alias["AliasName"] == f"alias/{alias_name}":
                kms_key_id = alias["TargetKeyId"]
                break

        if kms_key_id:
            kms_client.schedule_key_deletion(KeyId=kms_key_id, PendingWindowInDays=7)
            print(f"Scheduled deletion for KMS key with alias: {alias_name}")
        else:
            print(f"No KMS key found for alias: {alias_name}")

        # Delete all images in ECR repository
        images = ecr_client.list_images(repositoryName=f"{resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket")["imageIds"]
        if images:
            ecr_client.batch_delete_image(repositoryName=f"{resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket", imageIds=images)
            print(f"Deleted images from ECR repository: {resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket")

            ecr_client.delete_repository(repositoryName=f"{resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket", force=True)
            print(f"Deleted ECR repository: {resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket")
            
        print(f"No images found in ECR repository: {resources['instance_id']}-lambda-docker-{resources['instance_type']}-bucket")

        return {"status": "success", "message": "AWS resources offboarded successfully"}
    
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS error: {e.response['Error']['Message']}")
    






@app.get("/db/init")
async def initDB():
    try:
        response_workspaces = db.insert_workspaces()
        
        if "error" in response_workspaces:
            logger.error(f"Error inserting workspaces: {response_workspaces['error']}")
            raise HTTPException(status_code=500, detail=response_workspaces['error'])

        response_user = db.create_default_user()
        
        if "error" in response_user:
            logger.error(f"Error creating default user: {response_user['error']}")
            raise HTTPException(status_code=500, detail=response_user['error'])

        return {
            "DB initialized successfully.": response_workspaces['message'],
            "Default user created successfully.": response_user['message']
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1001)
