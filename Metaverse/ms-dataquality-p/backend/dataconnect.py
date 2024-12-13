import json
import time
import logging
from .aws_utils_testing import AWSUtils
from .gitlab_utils import GitLabUtils
from .database import Database
from botocore.exceptions import ClientError
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataconnectBackend:
    def __init__(self):
        self.db = Database()
        self.gl_utils = GitLabUtils()

    # 14-11-2024 implement method to verify if the lambda is already deployed by the pipline
    async def check_lambda_existence(self, dataconnect):
        """Check if the Lambda function exists to avoid redeployment."""
        aws_utils = AWSUtils()
        function_name = f"{dataconnect.instance_id}_{dataconnect.instance_type}_lambda"
        try:
            await asyncio.to_thread(aws_utils.lambda_client.get_function, FunctionName=function_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Lambda function '{function_name}' does not exist. Deployment required.")
                return False
            else:
                logger.error(f"Error checking Lambda existence: {e}")
                raise

    def get_user_dataconnects(self, user_id, workspace_id):
        try:
            # Call the function from the db file to retrieve the instances
            instances = self.db.get_user_instances_by_workspace(user_id, workspace_id)

            # Check if any instances were retrieved
            if instances:
                result = []
                for instance in instances:
                    instance_data = {
                        'dataconnect_id': instance.get('id'),
                        'user_id': instance.get('user_id'),
                        'user_id_variable': instance.get('user_id_variable'),
                        'instance_id': instance.get('instance_id'),
                        'instance_type': instance.get('instance_type'),
                        'workspace_id': instance.get('workspace_id')
                    }

                    # Handle 's3' instance type
                    if instance['instance_type'] == 's3':
                        instance_data['region'] = instance.get('region', '')
                        instance_data['key'] = instance.get('key', '')
                        instance_data['secret_key'] = instance.get('secret_key', '')

                    # Handle 'google_drive' instance type
                    elif instance['instance_type'] == 'google_drive':
                        instance_data['client_secret'] = instance.get('client_secret', '')
                        instance_data['client_id'] = instance.get('client_id', '')
                        instance_data['refresh_token'] = instance.get('refresh_token', '')

                    # Append instance data to the result list
                    result.append(instance_data)

                return result
            else:
                return []  # Return an empty list if no instances are found

        except Exception as e:
            logger.error(f"Error fetching user dataconnects: {e}")
            return []


    #21-08-2024 Function that retrieves all datasets for a given user across all their dataconnect instances.
    def get_all_datasets(self, user_id):
        dataconnects = self.get_user_dataconnects(user_id)
        all_datasets = []

        for dataconnect in dataconnects:
            self.update_datasets_for_dataconnect(dataconnect)
            datasets = self.get_datasets_for_dataconnect(dataconnect['dataconnect_id'])
            all_datasets.extend(datasets)

        return all_datasets

    #22-08-2024 - updated 14-11-2024
    async def get_buckets(self, dataconnect):
        aws_utils = AWSUtils()
        function_name = f"{dataconnect.instance_id}_{dataconnect.instance_type}_lambda"

        payload = {
            "user_id": dataconnect.user_id,
            "instance_id": dataconnect.instance_id,
            "instance_type": dataconnect.instance_type,
            "operation": "list_buckets"
        }

        try:
            bucket_response = await asyncio.to_thread(aws_utils.invoke_lambda, function_name, payload)

            if bucket_response and bucket_response.get('statusCode') == 200:
                buckets_info = json.loads(bucket_response['body'])
                buckets = buckets_info.get('buckets', [])

                # Ensure buckets is always an iterable (even if empty)
                if not buckets:
                    return [], None

                # Return a list of bucket details (name and region)
                return [{"bucket_name": bucket['name'], "bucket_region": bucket.get('region', 'Unknown')} for bucket in buckets], None
            else:
                return [], "Failed to retrieve buckets"
        
        except Exception as e:
            logger.error(f"Error invoking Lambda function in get_buckets: {e}")
            return [], f"Error invoking Lambda function: {str(e)}"


    
    #22-08-2024 - updated 14-11-2024
    async def get_bucket_files(self, dataconnect, selected_bucket):
        aws_utils = AWSUtils()
        function_name = f"{dataconnect.instance_id}_{dataconnect.instance_type}_lambda"

        payload = {
            "user_id": dataconnect.user_id,
            "instance_id": dataconnect.instance_id,
            "instance_type": dataconnect.instance_type,
            "operation": "list_files",
            "bucket_name": selected_bucket
        }

        try:
            file_response = await asyncio.to_thread(aws_utils.invoke_lambda, function_name, payload)

            if file_response and file_response.get('statusCode') == 200:
                files_data = json.loads(file_response['body'])
                files = files_data.get('files', [])
                return files, None
            else:
                return [], f"Failed to retrieve files from bucket: {selected_bucket}" 
            
        except Exception as e:
            logger.error(f"Error invoking Lambda function in get_buckets_files: {e}")
            return [], f"Error invoking Lambda function: {str(e)}"

    
    # Get  folders from google drive
    def get_google_drive_folders(self, dataconnect):

        #11-09-2024
        aws_utils = AWSUtils()
        function_name = f"{dataconnect.instance_id}_{dataconnect.instance_type}_lambda" # Remove _{dataconnect.user_id} as the lambda name has a limit of 64 char
        
        payload = {
            "user_id": dataconnect.user_id,
            "instance_id": dataconnect.instance_id,
            "instance_type": dataconnect.instance_type,
            "action": "list_folders"
        }

        try:
            folder_response = aws_utils.invoke_lambda(function_name, payload)
            if folder_response and folder_response.get('statusCode') == 200:
                folders_data = json.loads(folder_response['body'])
                return folders_data, None
            else:
                return None, "Failed to retrieve folders from Google Drive"
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {e}")
            return None, f"Error invoking Lambda function: {str(e)}"

    # get files based on selected folder from google drive
    def get_google_drive_files(self, dataconnect, selected_folder):

        aws_utils = AWSUtils()
        function_name = f"{dataconnect['instance_id']}_{dataconnect['instance_type']}_lambda" # Remove _{dataconnect.user_id} as the lambda name has a limit of 64 char
        
        payload = {
            "user_id": dataconnect['user_id'],
            "instance_id": dataconnect['instance_id'],
            "instance_type": dataconnect['instance_type'],
            "action": "list_files",
            "folder_id": selected_folder
        }

        try:
            file_response = aws_utils.invoke_lambda(function_name, payload)
            if file_response and file_response.get('statusCode') == 200:
                files_data = json.loads(file_response['body'])
                return files_data, None
            else:
                return None, f"Failed to retrieve files from folder: {selected_folder}"
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {e}")
            return None, f"Error invoking Lambda function: {str(e)}"

    def delete_dataconnect(self, user_id, instance_id, instance_type):
        variables = [
            {'key': 'USER_ID', 'value': user_id},
            {'key': 'INSTANCE_ID', 'value': instance_id},
            {'key': 'INSTANCE_TYPE', 'value': instance_type},
            {'key': 'DELETE_RESOURCES', 'value': True},
        ]
        try:
            pipeline = self.gl_utils.trigger_pipeline(variables=variables)

            while True:
                status = self.gl_utils.check_pipeline_status(pipeline.id)
                if status in ['success', 'failed']:
                    break
                time.sleep(5)

            if status == 'success':
                db_delete_success = self.db.delete_user_detail(user_id, instance_id, instance_type)
                return True, db_delete_success, pipeline.id
            else:
                return False, False, pipeline.id
        except Exception as e:
            logger.error(f"Error deleting dataconnect: {e}")
            return False, False, None