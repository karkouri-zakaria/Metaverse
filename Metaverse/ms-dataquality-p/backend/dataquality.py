from datetime import datetime
from io import StringIO
import traceback
from aiohttp import ClientError
import boto3
from .spark_session import create_spark_session
from .dataconnect import DataconnectBackend
import pandas as pd
from .api_mistral import generate_quality_rules_with_sql
import os
import re
from backend.database import Database
import logging
from dotenv import load_dotenv

env_file = '.env'
load_dotenv(env_file, override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQualityService:
    def __init__(self, ):
        self.dataconnect = DataconnectBackend()
        self.spark = create_spark_session()
        self.api_key = os.getenv('MISTRAL_API_KEY')
        self.db = Database()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('ACCESS_KEY'),
            aws_secret_access_key=os.getenv('SECRET_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.region = os.getenv('AWS_REGION')

    def get_dataconnect_datasets(self, user_id, workspace_id):
        datasets = self.dataconnect.get_all_datasets(user_id, workspace_id)
        print(f"datasets :{datasets}")
        return [{"id": d['id'], "name": d['name']} for d in datasets]

    def clean_sql_script(self, script):
        script = re.sub(r'```sql|```', '', script)
        script = script.strip()
        script = re.sub(r'\s+', ' ', script)
        script = re.sub(r'\([^)]*\)', '', script)
        return script
    
    def ensure_bucket_exists(self, bucket_name):
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' already exists.")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"Bucket '{bucket_name}' does not exist. Creating it now.")
                # Create bucket with specified region if necessary
                create_bucket_params = {'Bucket': bucket_name}
                if self.region != 'us-east-1':  # us-east-1 does not require location constraint
                    create_bucket_params['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.region
                    }
                self.s3_client.create_bucket(**create_bucket_params)
            else:
                raise e  # Re-raise other errors

    def extract_datasets_from_s3(self, dataconnect_datasets):
        s3_datasets = []
        for dataset in dataconnect_datasets:
            logger.info(f"Processing dataset: {dataset}")
            
            if isinstance(dataset, dict):
                source = self.db.get_datasource_by_id(dataset.get('datasource_id'))
                # If dataset is already a dictionary, use it as is
                dataconnect_id = dataset.get('id')
                bucket_name = source[0]['name']
                file_name = dataset.get('name')
                file_size = dataset.get('file_size')
                last_modified = dataset.get('last_modified')
                file_type = dataset.get('dataset_type')
            elif isinstance(dataset, (list, tuple)) and len(dataset) >= 7:
                # If dataset is a list or tuple, unpack it
                dataconnect_id, bucket_name, file_name, file_size, last_modified, file_type = dataset[1:7]
            else:
                logger.error(f"Unexpected dataset format: {type(dataset)}")
                continue
            s3_path = f"s3a://{bucket_name}/{file_name}"
            try:
                if file_type.lower() == 'csv':
                    df = self.spark.read.csv(s3_path, header=True, inferSchema=True)
                elif file_type.lower() == 'excel':
                    df = self.spark.read.format("com.crealytics:spark-excel_2.11:0.13.5") \
                        .option("header", "true") \
                        .option("inferSchema", "true") \
                        .load(s3_path)
                elif file_type.lower() == 'sql':
                    df = self.spark.read.text(s3_path).withColumnRenamed("value", "sql_content")
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")

                rules = {}
                for column in df.columns:
                    logger.info(f"Generating quality rules for column: {column}")
                    rules[column] = generate_quality_rules_with_sql(self.api_key, column)

                s3_datasets.append({
                    'dataframe': df,
                    'metadata': {
                        'dataconnect_id': dataconnect_id,
                        'bucket_name': bucket_name,
                        'file_name': file_name,
                        'file_size': file_size,
                        'last_modified': last_modified,
                        'file_type': file_type
                    },
                    'rules': rules
                })
            except Exception as e:
                logger.warning(f"Error reading dataset {s3_path}: {str(e)}")
        return s3_datasets

    def generate_and_save_rules(self, dataset):
        try:
            df = dataset['dataframe']
            metadata = dataset['metadata']
            rules = dataset['rules']

            # Extract file name without extension to use as table name
            file_name = os.path.splitext(metadata['file_name'])[0]
            table_name = re.sub(r'\W+', '_', file_name)

            rows = []
            for column, content in rules.items():
                individual_rules = content.split('Rule:')
                for rule in individual_rules[1:]:
                    rule = rule.strip()
                    try:
                        rule_parts = rule.split('SQL Query:', 1)
                        if len(rule_parts) == 2:
                            rule_name = rule_parts[0].strip()
                            sql_script = self.clean_sql_script(rule_parts[1].strip())
                            sql_script = sql_script.replace('table_name', table_name)
                            rows.append({'Column': column, 'Rule': rule_name, 'SQL Query': sql_script})
                    except Exception as e:
                        print(f"Error processing rule: {str(e)}")
                        traceback.print_exc()

            rules_df = pd.DataFrame(rows)

            # Set up S3 bucket name and output file name
            bucket_name = "quality-rules"
            current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = datetime.now().strftime("%Y%m%d")
            output_file = f"{folder_name}/{file_name}_{current_datetime}_generated_rules.csv"

            # Ensure bucket exists
            self.ensure_bucket_exists(bucket_name)

            # Convert DataFrame to CSV and upload to S3
            csv_buffer = StringIO()
            rules_df.to_csv(csv_buffer, header=True, index=False)
            self.s3_client.put_object(Bucket=bucket_name, Key=output_file, Body=csv_buffer.getvalue())
            print(f"Generated rules saved to: s3://{bucket_name}/{output_file}")

            return rules_df

        except Exception as e:
            print(f"Error in generate_and_save_rules: {str(e)}")
            traceback.print_exc()
            return pd.DataFrame(columns=['Column', 'Rule', 'SQL Query'])


    def process_selected_dataset(self, dataset):
        logger.info(f"Processing dataset with ID: {dataset}")
        logger.info(dataset["id"])
        selected_data = self.db.get_dataset_by_id(dataset["id"])
        if not selected_data:
            logger.warning(f"No dataset found with ID: {dataset}")
            return None
        logger.info(f"Selected data: {selected_data}")
        s3_datasets = self.extract_datasets_from_s3(selected_data)
        logger.info(f"display s3_datasets: {s3_datasets}")
        if s3_datasets:
            dataset = s3_datasets[0]
            logger.info(f"Dataset meatada: {dataset['metadata']}")
            rules_df = self.generate_and_save_rules(dataset)

            df_json = dataset['dataframe'].toPandas().to_dict(orient='records')
            rules_json = rules_df.to_dict(orient='records')

            result = {
                "dataframe": df_json,
                "metadata": dataset['metadata'],
                "rules": rules_json
            }
            logger.info(f"Processed result keys: {result.keys()}")
            return result
        logger.warning("No S3 datasets found")
        return None
    
    def extract_datasets_from_s3_only(self, dataconnect_datasets):
        s3_datasets = []
        for dataset in dataconnect_datasets:
            if isinstance(dataset, dict):
                source = self.db.get_datasource_by_id(dataset.get('datasource_id'))
                bucket_name = source[0]['name']
                file_name = dataset.get('name')
                file_type = dataset.get('dataset_type')
            elif isinstance(dataset, (list, tuple)) and len(dataset) >= 7:
                # If dataset is a list or tuple, unpack it
                dataconnect_id, bucket_name, file_name, file_size, last_modified, file_type = dataset[1:7]
            else:
                logger.error(f"Unexpected dataset format: {type(dataset)}")
                continue
            s3_path = f"s3a://{bucket_name}/{file_name}"
            try:
                if file_type.lower() == 'csv':
                    df = self.spark.read.csv(s3_path, header=True, inferSchema=True)
                elif file_type.lower() == 'excel':
                    df = self.spark.read.format("com.crealytics:spark-excel_2.11:0.13.5") \
                        .option("header", "true") \
                        .option("inferSchema", "true") \
                        .load(s3_path)
                elif file_type.lower() == 'sql':
                    df = self.spark.read.text(s3_path).withColumnRenamed("value", "sql_content")
                else:
                    raise ValueError(f"Unsupported file type: {file_type}")


                s3_datasets.append({
                    'dataframe': df.toPandas().to_dict(orient='records')
                })
            except Exception as e:
                logger.warning(f"Error reading dataset {s3_path}: {str(e)}")
        return s3_datasets

    def stop_spark(self):
        if self.spark:
            self.spark.stop()