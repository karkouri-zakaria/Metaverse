import os
import json
import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from botocore.exceptions import ClientError
import base64
import logging
from datetime import datetime, timezone

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
USER_ID = os.environ['USER_ID']
INSTANCE_ID = os.environ['INSTANCE_ID']
INSTANCE_TYPE = os.environ['INSTANCE_TYPE']
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
print(USER_ID, INSTANCE_ID, INSTANCE_TYPE, AWS_REGION)

def decrypt(ciphertext):
    kms = boto3.client('kms', region_name=AWS_REGION)
    try:
        response = kms.decrypt(CiphertextBlob=base64.b64decode(ciphertext))
        return response['Plaintext'].decode('utf-8')
    except ClientError as e:
        logger.error(f"Error decrypting: {e}")
        return None

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name=AWS_REGION)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        return None

def create_drive_service(client_id, client_secret, refresh_token):
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

def get_file_type(file_name):
    # Détermine le type de fichier à partir de son extension
    ext = file_name.split('.')[-1].lower()
    if ext in ['csv']:
        return 'CSV'
    elif ext in ['sql']:
        return 'SQL'
    elif ext in ['xlsx', 'xls']:
        return 'Excel'
    else:
        return 'Unknown'
#04-09-2024
def list_top_level_folders(drive_service):
    try:
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and 'root' in parents",
            pageSize=20,
            fields="nextPageToken, files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        processed_folders = []
        
        for folder in folders:
            processed_folder = {
                'id': folder['id'],
                'name': folder['name'],
            }
            processed_folders.append(processed_folder)
        
        return processed_folders
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        raise

#04-09-2024
def list_files_in_folder(drive_service, folder_id):
    try:
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=20,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, trashed)"
        ).execute()
        
        files = results.get('files', [])
        processed_files = []
        
        for file in files:
            file_type = get_file_type(file['name'])
            last_scan = datetime.now(timezone.utc).isoformat()
            
            processed_file = {
                'file_name': file['name'],
                'connection_status': 'connected',
                'type': file_type,
                'last_scan': last_scan
                # 'id': file['id'],
                # 'size': file.get('size'),
                # 'modified_time': file.get('modifiedTime'),
                # 'created_time': file.get('createdTime'),
                # 'trashed': file.get('trashed', False)
            }
            processed_files.append(processed_file)
        
        return processed_files
    except Exception as e:
        logger.error(f"Error listing files in folder: {e}")
        raise


def lambda_handler(event, context):
    secret_name = f"{USER_ID}_{INSTANCE_ID}_{INSTANCE_TYPE}_secrets"

    secrets = get_secret(secret_name)
    if not secrets:
        return {
            'statusCode': 500,
            'body': json.dumps('Error retrieving secrets.')
        }

    required_keys = ['ENCRYPTED_CLIENT_ID', 'ENCRYPTED_CLIENT_SECRET', 'ENCRYPTED_REFRESH_TOKEN']
    if not all(key in secrets for key in required_keys):
        return {
            'statusCode': 400,
            'body': json.dumps('Encrypted credentials are required.')
        }

    try:
        client_id = decrypt(secrets['ENCRYPTED_CLIENT_ID'])
        client_secret = decrypt(secrets['ENCRYPTED_CLIENT_SECRET'])
        refresh_token = decrypt(secrets['ENCRYPTED_REFRESH_TOKEN'])

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("Failed to decrypt credentials.")

        drive_service = create_drive_service(client_id, client_secret, refresh_token)
        
        action = event.get('action')

        if action == 'list_folders':
            folders = list_top_level_folders(drive_service)
            return {
                'statusCode': 200,
                'body': json.dumps({'buckets': folders})
            }
        elif action == 'list_files':
            folder_id = event.get('folder_id')
            if not folder_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Folder ID is required for listing files.')
                }
            files = list_files_in_folder(drive_service, folder_id)

            return {
                'statusCode': 200,
                'body': json.dumps({'files': files})
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid action. Use "list_folders" or "list_files".')
            }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }