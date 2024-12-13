import uuid
import boto3
import hashlib
import botocore
import streamlit as st
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Load environment variables
env_file = '.env'
load_dotenv(env_file, override=True)

class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Check if an instance already exists
        if cls._instance is None:
            # If not, create a new instance and assign it to the class variable
            cls._instance = super(Database, cls).__new__(cls)
        # Return the existing instance (new or previously created)
        return cls._instance
    

    def __init__(self):

        # Only perform initialization logic once
        if not hasattr(self, '_initialized'):
            encryption_key = os.getenv('ENCRYPTION_KEY')
            aws_access_key = os.getenv('ACCESS_KEY')
            aws_secret_key = os.getenv('SECRET_KEY')
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            self.cipher = Fernet(encryption_key)

            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )

            self.dynamodb_client = boto3.client(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            
            # Create tables if they don't exist
            self.create_tables()

            # Mark the instance as initialized to prevent re-initialization
            self._initialized = True

    def list_existing_tables(self):
        """Helper function to list existing DynamoDB tables."""
        try:
            return self.dynamodb_client.list_tables()['TableNames']
        except ClientError as e:
            print(f"Error listing tables: {e}")
            return []

    def create_tables(self):
        self.users_table = self.create_users_table()
        self.workspaces_table = self.create_workspaces_table()
        self.dataconnects_table = self.create_dataconnects_table()
        self.datasources_table = self.create_datasources_table()
        self.datasets_table = self.create_datasets_table()

    def encrypt(self, data):
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data):
        return self.cipher.decrypt(encrypted_data.encode()).decode()
        


    def create_users_table(self):
        try:
            existing_tables = self.list_existing_tables()
            if 'users' in existing_tables:
                print("Users table already exists.")
                return self.dynamodb.Table('users')

            table = self.dynamodb.create_table(
                TableName='users',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'username', 'KeyType': 'RANGE'}  # Sort key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},  
                    {'AttributeName': 'username', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                },
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'username-index',
                        'KeySchema': [
                            {'AttributeName': 'username', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 10,
                            'WriteCapacityUnits': 10
                        }
                    }
                ]
            )
            table.wait_until_exists()
            print("Users table created successfully")
            return table

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print("Users table already exists.")
            else:
                print(f"Unexpected error: {e}")


    def create_workspaces_table(self):
        try:
            existing_tables = self.list_existing_tables()
            if 'workspaces' in existing_tables:
                print("Workspaces table already exists.")
                return self.dynamodb.Table('workspaces')

            table = self.dynamodb.create_table(
                TableName='workspaces',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
            print("Workspaces table created successfully")
            return table

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print("Workspaces table already exists.")
            else:
                print(f"Unexpected error: {e}")


    def create_dataconnects_table(self):
        try:
            existing_tables = self.list_existing_tables()
            if 'dataconnects' in existing_tables:
                print("Dataconnects table already exists.")
                return self.dynamodb.Table('dataconnects')

            table = self.dynamodb.create_table(
                TableName='dataconnects',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},   # Primary key
                    {'AttributeName': 'user_id', 'KeyType': 'RANGE'}  # Secondary key for relationship with users
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},  # Primary key
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},  # Relation to users
                    {'AttributeName': 'workspace_id', 'AttributeType': 'S'}  # Relationship with workspaces
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'user_id-workspace_id-index',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'workspace_id', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'instance_id-index',
                        'KeySchema': [
                            {'AttributeName': 'id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            table.wait_until_exists()
            print("Dataconnects table created successfully")
            return table

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print("Dataconnects table already exists.")
            else:
                print(f"Unexpected error: {e}")


    def create_datasources_table(self):
        try:
            existing_tables = self.list_existing_tables()
            if 'datasources' in existing_tables:
                print("Datasources table already exists.")
                return self.dynamodb.Table('datasources')

            table = self.dynamodb.create_table(
                TableName='datasources',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Primary key
                    {'AttributeName': 'instance_id', 'KeyType': 'RANGE'}  # Secondary key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'instance_id', 'AttributeType': 'S'},
                    {'AttributeName': 'name', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'name-instance_id-index',
                        'KeySchema': [
                            {'AttributeName': 'name', 'KeyType': 'HASH'},
                            {'AttributeName': 'instance_id', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'instance_id-index',  # New GSI to query by instance_id
                        'KeySchema': [
                            {'AttributeName': 'instance_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'source-id-index',  # New GSI to query by id
                        'KeySchema': [
                            {'AttributeName': 'id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
            print("Datasources table created successfully")
            return table

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print("Datasources table already exists.")
            else:
                print(f"Unexpected error: {e}")


    def create_datasets_table(self):
        try:
            existing_tables = self.list_existing_tables()
            if 'datasets' in existing_tables:
                print("Datasets table already exists.")
                return self.dynamodb.Table('datasets')

            table = self.dynamodb.create_table(
                TableName='datasets',
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'},  # Primary key
                    {'AttributeName': 'datasource_id', 'KeyType': 'RANGE'}  # Relationship with datasources
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'S'},
                    {'AttributeName': 'datasource_id', 'AttributeType': 'S'},
                    {'AttributeName': 'name', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'name-datasource_id-index',
                        'KeySchema': [
                            {'AttributeName': 'name', 'KeyType': 'HASH'},  # HASH key for the index
                            {'AttributeName': 'datasource_id', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'source-id-index',
                        'KeySchema': [
                            {'AttributeName': 'datasource_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'id-index',
                        'KeySchema': [
                            {'AttributeName': 'id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
            print("Datasets table created successfully")
            return table

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print("Datasets table already exists.")
            else:
                print(f"Unexpected error: {e}")




    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, stored_password, provided_password):
        return stored_password == self.hash_password(provided_password)

    def get_user(self, username):
        try:
            response = self.users_table.query(
                IndexName='username-index', 
                KeyConditionExpression=Key('username').eq(username)
            )
            return response.get('Items', [])
        except ClientError as e:
            st.error(f"An error occurred: {e}")
            return None


    def get_username_from_user_id(self, user_id):
        try:
            response = self.users_table.get_item(Key={'id': user_id})
            return response['Item']['username'] if 'Item' in response else None
        except ClientError as e:
            st.error(f"An error occurred: {e}")
            return None
        
    def get_instance_by_id(self, instance_id):
        try:
            response = self.dataconnects_table.query(
                IndexName='instance_id-index',
                KeyConditionExpression=Key('id').eq(instance_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None
        
    def get_user_instances_by_workspace(self, user_id, workspace_id):
        try:
            response = self.dataconnects_table.query(
                IndexName='user_id-workspace_id-index',
                KeyConditionExpression=Key('user_id').eq(user_id) & Key('workspace_id').eq(workspace_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            st.error(f"An error occurred: {e}")
            return None
        
    def get_instance_sources(self, instance_id):
        try:
            response = self.datasources_table.query(
                IndexName='instance_id-index',
                KeyConditionExpression=Key('instance_id').eq(instance_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None


    def get_source_files(self, source_id):
        try:
            response = self.datasets_table.query(
                IndexName='source-id-index',
                KeyConditionExpression=Key('datasource_id').eq(source_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None
        
    def get_datasource_by_id(self, datasource_id):
        try:
            response = self.datasources_table.query(
                IndexName='source-id-index',
                KeyConditionExpression=Key('id').eq(datasource_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None
        
    def get_dataset_by_id(self, dataset_id):
        try:
            response = self.datasets_table.query(
                IndexName='id-index', 
                KeyConditionExpression=Key('id').eq(dataset_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"An error occurred: {e}")
            return None

        
    def add_user(self, username, password):
        hashed_pw = self.hash_password(password)
        try:
            user_id = str(uuid.uuid4()) 
            self.users_table.put_item(
                Item={
                    'id': user_id,
                    'username': username,
                    'password': hashed_pw
                }
            )
            return user_id
        except ClientError as e:
            st.error(f"An error occurred: {e}")

    def insert_workspace(self, name, description):
        try:
            workspace_id = str(uuid.uuid4()) 
            self.workspaces_table.put_item(
                Item={
                    'id': workspace_id,
                    'name': name,
                    'description': description
                }
            )
            return workspace_id
        except ClientError as e:
            st.error(f"An error occurred: {e}")


    def insert_dataconnect(self, dataconnect):
        try:
            dataconnect_id = str(uuid.uuid4()) 
            
            item = {
                'id': dataconnect_id,
                'user_id': dataconnect.user_id,
                'workspace_id': dataconnect.workspace_id,
                'user_id_variable': dataconnect.user_id_variable,
                'instance_id': dataconnect.instance_id,
                'instance_type': dataconnect.instance_type
            }
            
            
            if dataconnect.instance_type == 's3':
                item.update({
                    'key': self.encrypt(dataconnect.key),
                    'secret_key':  self.encrypt(dataconnect.aws_secret_access_key),
                    'region':  self.encrypt(dataconnect.region)
                })
            elif dataconnect.instance_type == 'google_drive':
                item.update({
                    'client_secret':  self.encrypt(dataconnect.drive_client_secret),
                    'client_id':  self.encrypt(dataconnect.drive_client_id),
                    'refresh_token':  self.encrypt(dataconnect.drive_refresh_token)
                })
            
            
            self.dataconnects_table.put_item(Item=item)
            return dataconnect_id
        except ClientError as e:
            st.error(f"An error occurred: {e}")


    def insert_datasource(self, datasource, instance_id):
        try:
            datasource_id = str(uuid.uuid4()) 
            self.datasources_table.put_item(
                Item={
                    'id': datasource_id,
                    'name': datasource.name,
                    'instance_id': instance_id
                }
            )
            return datasource_id 
        except ClientError as e:
            st.error(f"An error occurred: {e}")

    def insert_dataset(self, dataset, datasource_id):
        try:
            dataset_id = str(uuid.uuid4()) 
            self.datasets_table.put_item(
                Item={
                    'id': dataset_id,
                    'name': dataset.name,
                    'datasource_id': datasource_id,
                    'connexion_status': dataset.connexion_status,
                    'dataset_type': dataset.dataset_type,
                    'last_scan': dataset.last_scan,
                    'column_delimiter': dataset.column_delimiter,
                    'excape_char': dataset.excape_char
                }
            )
            return dataset_id
        except ClientError as e:
            st.error(f"An error occurred: {e}")

    def set_default_aws_credentials(self, user_id, aws_access_key, aws_secret_key, aws_region):
        try:
            self.aws_credentials_table.put_item(
                Item={
                    'user_id': user_id,
                    'aws_access_key': aws_access_key,
                    'aws_secret_key': aws_secret_key,
                    'aws_region': aws_region
                }
            )
        except ClientError as e:
            st.error(f"An error occurred while setting default AWS credentials: {e}")

    def get_default_aws_credentials(self, user_id):
        try:
            response = self.aws_credentials_table.get_item(Key={'user_id': user_id})
            return response.get('Item', None)
        except ClientError as e:
            st.error(f"An error occurred while retrieving default AWS credentials: {e}")
            return None

    def delete_user_detail(self, user_id_variable, instance_id, instance_type):
        try:
            self.dataconnects_table.delete_item(
                Key={
                    'user_id_variable': user_id_variable,
                    'instance_id': instance_id
                },
                ConditionExpression=boto3.dynamodb.conditions.Key('instance_type').eq(instance_type)
            )
        except ClientError as e:
            st.error(f"An error occurred: {e}")


    def insert_workspaces(self):
        workspaces = [
            {'id': str(uuid.uuid4()), 'name': 'Workspace A', 'description': 'Description for Workspace A'},
            {'id': str(uuid.uuid4()), 'name': 'Workspace B', 'description': 'Description for Workspace B'},
            {'id': str(uuid.uuid4()), 'name': 'Workspace C', 'description': 'Description for Workspace C'}
        ]
        
        try:
            for workspace in workspaces:
                self.workspaces_table.put_item(Item=workspace)
            return {"message": "All workspaces inserted successfully."}
        except ClientError as e:
            error_message = f"Error inserting workspaces: {e.response['Error']['Message']}"
            print(error_message)
            return {"error": error_message} 
        
    def create_default_user(self):
        
        default_user = {
            'id': str(uuid.uuid4()), 
            'username': 'admin',
            'password': self.hash_password('admin') 
        }

        try:
            
            self.users_table.put_item(Item=default_user)
            return {"message": "Default user created successfully."}
        except ClientError as e:
            error_message = f"Error creating default user: {e.response['Error']['Message']}"
            print(error_message)
            return {"error": error_message} 
        
    def get_user_workspaces(self, user_id):
        try:
            
            response = self.dataconnects_table.query(
                IndexName='user_id-workspace_id-index',
                KeyConditionExpression=Key('user_id').eq(user_id)
            )

            unique_workspace_ids = set(item['workspace_id'] for item in response['Items'])

            keys = [{'id': {'S': workspace_id}} for workspace_id in unique_workspace_ids]

            response = self.dynamodb_client.batch_get_item(
                RequestItems={
                    'workspaces': {
                        'Keys': keys 
                    }
                }
            )

            workspaces = response.get('Responses', {}).get('workspaces', [])
            return workspaces if workspaces else []

        except botocore.exceptions.ClientError as e:
            print(f"An error occurred: {e}")
            return None
        

    def delete_dataconnect_and_related_records(self, dataconnect_id):
        try:
            # Step 1: Delete the dataconnect record and get its instance_id
            dataconnect_response = self.dataconnects_table.query(
                IndexName='instance_id-index',
                KeyConditionExpression=Key('id').eq(dataconnect_id)
            )

            if 'Items' not in dataconnect_response:
                print(f"No dataconnect record found with id {dataconnect_id}")
                return

            dataconnect_record = dataconnect_response.get('Items', [])[0]
            instance_id = dataconnect_record['instance_id']  # Replace with the correct key for instance_id if different
            user_id = dataconnect_record['user_id'] 
            workspace_id = dataconnect_record['workspace_id'] 

            # Delete the dataconnect record
            self.dataconnects_table.delete_item(Key={'id': dataconnect_id, 'user_id': user_id})
            print(f"Deleted dataconnect record with id {dataconnect_id}")

            # Step 2: Delete all records from datasources table with the same instance_id
            datasource_response = self.datasources_table.query(
                IndexName='instance_id-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('instance_id').eq(instance_id)
            )
            datasources_to_delete = datasource_response.get('Items', [])

            for datasource in datasources_to_delete:
                datasource_id = datasource['id']
                self.datasources_table.delete_item(Key={'id': datasource_id, 'instance_id': instance_id})
                print(f"Deleted datasource record with id {datasource_id}")

                # Step 3: Delete all records from datasets table with the same datasource_id
                datasets_response = self.datasets_table.query(
                    IndexName='source-id-index',
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('datasource_id').eq(datasource_id)
                )
                datasets_to_delete = datasets_response.get('Items', [])

                for dataset in datasets_to_delete:
                    self.datasets_table.delete_item(Key={'id': dataset['id'], 'datasource_id': datasource_id})
                    print(f"Deleted dataset record with id {dataset['id']}")

            print("All related records have been deleted successfully.")
            return {"status": "success", "message": "Datasource instances and related records have deleted successfully."}

        except Exception as e:
            print(f"An error occurred: {e}")






