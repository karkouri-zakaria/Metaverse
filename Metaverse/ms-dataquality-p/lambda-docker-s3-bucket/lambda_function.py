import json
import boto3
import os
import base64
from botocore.exceptions import ClientError

USER_ID = os.environ['USER_ID']
INSTANCE_ID = os.environ['INSTANCE_ID']
INSTANCE_TYPE = os.environ['INSTANCE_TYPE']
print(USER_ID, INSTANCE_ID, INSTANCE_TYPE)


def decrypt(ciphertext):
    kms = boto3.client('kms')
    try:
        response = kms.decrypt(CiphertextBlob=base64.b64decode(ciphertext))
        return response['Plaintext'].decode('utf-8')
    except ClientError as e:
        print(f"Erreur lors du déchiffrement: {e}")
        return None

def get_secret(secret_name):
    # Crée un client Secrets Manager
    client = boto3.client('secretsmanager')

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(f"Erreur lors de la récupération du secret: {e}")
        return None

    # Décrypte le secret à l'aide de la clé KMS associée.
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


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


def lambda_handler(event, context):
    secret_name = f"{event['user_id']}_{event['instance_id']}_{event['instance_type']}_secrets"
    
    secrets = get_secret(secret_name)
    if not secrets:
        return {
            'statusCode': 500,
            'body': json.dumps('Error retrieving secrets.')
        }

    encrypted_access_key = secrets.get('ENCRYPTED_ACCESS_KEY')
    encrypted_secret_key = secrets.get('ENCRYPTED_SECRET_KEY')
    region = secrets.get('REGION')

    if not encrypted_access_key or not encrypted_secret_key or not region:
        return {
            'statusCode': 400,
            'body': json.dumps('Encrypted credentials are required.')
        }

    access_key = encrypted_access_key
    secret_key = encrypted_secret_key

    if not access_key or not secret_key or not region:
        return {
            'statusCode': 500,
            'body': json.dumps('Error during encryption credentials.')
        }
    
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        s3 = session.client('s3')

        operation = event.get('operation', 'list_buckets')

        if operation == 'list_buckets':
            # List all buckets
            response = s3.list_buckets()
            buckets = [{'name': bucket['Name'], 'creation_date': bucket['CreationDate'].isoformat()} 
                       for bucket in response['Buckets']]
            return {
                'statusCode': 200,
                'body': json.dumps({'buckets': buckets})
            }
        elif operation == 'list_files':
            # List files in the specified bucket
            bucket_name = event.get('bucket_name')
            if not bucket_name:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Bucket name is required for listing files.')
                }
            
            """ response = s3.list_objects_v2(Bucket=bucket_name)
            files = [{'key': obj['Key'], 'size': obj['Size'], 'last_modified': obj['LastModified'].isoformat(), 'file_type':get_file_type()} 
                     for obj in response.get('Contents', [])] """
            
            #objects = s3.list_objects_v2(Bucket=bucket_name)
            response = s3.list_objects_v2(Bucket=bucket_name)
            files_info = list(map(lambda obj: {
                'file_name': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'file_type': get_file_type(obj['Key'])
            }, response['Contents']))

            
            """ files = [
                    {'key': obj['Key'], 
                    'size': obj['Size'], 
                    'last_modified': obj['LastModified'].isoformat(), 
                    'file_type': get_file_type(obj['Key'])} 
                    for obj in response.get('Contents', [])] """
            return {
                'statusCode': 200,
                'body': json.dumps({'files': files_info})
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Unsupported operation: {operation}")
            }
    
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error connecting to S3: {str(e)}")
        }