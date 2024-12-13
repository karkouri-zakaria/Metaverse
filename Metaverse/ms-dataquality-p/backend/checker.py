import traceback
from venv import logger
import pandas as pd
import boto3
from io import StringIO
import os
from dotenv import load_dotenv
import re
import pandasql as ps
from backend.database import Database
from backend.dataquality import DataQualityService

# Load environment variables from .env file
load_dotenv()

class DataQualityChecker:
    
    def __init__(self):
        self.db = Database()
        self.dqs = DataQualityService()
        # Initialize the S3 client with credentials from the .env file
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('ACCESS_KEY'),
            aws_secret_access_key=os.getenv('SECRET_KEY'),
            region_name=os.getenv('AWS_REGION')  # Optional
        )
        
    def load_rules_from_s3(self, bucket_name, csv_file_key):
        """
        Load the rules CSV from S3 and return it as a DataFrame.
        """
        response = self.s3_client.get_object(Bucket=bucket_name, Key=csv_file_key)
        csv_content = response['Body'].read().decode('utf-8')
        rules_df = pd.read_csv(StringIO(csv_content))
        return rules_df

    def clean_sql_script(self, script):
        """
        Cleans the SQL script by removing '**' marks and anything after the first semicolon.
        The semicolon is preserved as part of the query.
        """
        # Remove any '**' marks
        script = re.sub(r'\*\*', '', script)
        
        # Attempt to find the first semicolon
        match = re.search(r'.*?;', script)
        
        # Check if a match was found
        if match:
            # Keep only up to and including the first semicolon
            script = match.group(0)
        
        # Strip any leading/trailing whitespace
        return script.strip()



    def check_rule(self, df, rule_name, column, rule_sql):
        """
        Apply a rule dynamically based on the rule name and SQL script.
        """
        try:
            # Map rule names to check types (you can expand this)
            if "Not Null" in rule_name:
                invalid_count = df[column].isnull().sum()
                valid_count = len(df) - invalid_count
            elif "Unique" in rule_name:
                invalid_count = df[column].duplicated().sum()
                valid_count = len(df) - invalid_count
            elif "Positive Integer" in rule_name:
                invalid_count = df[df[column] <= 0].shape[0]
                valid_count = len(df) - invalid_count
            elif "Numeric" in rule_name:
                invalid_count = df[~df[column].apply(lambda x: str(x).isdigit())].shape[0]
                valid_count = len(df) - invalid_count
            elif "Length" in rule_name:
                length = int(re.findall(r'\d+', rule_name)[0])
                invalid_count = df[df[column].astype(str).str.len() != length].shape[0]
                valid_count = len(df) - invalid_count
            elif "No Leading Zeros" in rule_name:
                invalid_count = df[df[column].astype(str).str.startswith('0')].shape[0]
                valid_count = len(df) - invalid_count
            elif "Consistent Data Type" in rule_name:
                invalid_count = df[df[column].apply(lambda x: isinstance(x, int) or isinstance(x, float))].shape[0]
                valid_count = len(df) - invalid_count
            elif "Regex" in rule_name:
                pattern = rule_sql.strip()  # Assuming regex pattern is in SQL query
                invalid_count = df[~df[column].astype(str).str.match(pattern)].shape[0]
                valid_count = len(df) - invalid_count
            else:
                # Execute the rule as an SQL query on the DataFrame using pandasql
                query = re.sub(r'\bFROM\s+\w+', 'FROM df', rule_sql, flags=re.IGNORECASE)
                query = re.sub(r'\bCOUNT\b', 'COUNT(*)', query, flags=re.IGNORECASE)

                # Apply TRIM(column_name) and LENGTH(column_name) format fixes using the `column` variable
                query = re.sub(r'\bTRIM\b', f'TRIM({column})', query, flags=re.IGNORECASE)
                query = re.sub(r'\bLENGTH\b', f'LENGTH({column})', query, flags=re.IGNORECASE)

                query = re.sub(r'\bUPPER\b', f'UPPER({column})', query, flags=re.IGNORECASE)
                query = re.sub(r'\bLOWER\b', f'LOWER({column})', query, flags=re.IGNORECASE)

                query = re.sub(r'\bCHAR_LENGTH\b', f'CHAR_LENGTH({column})', query, flags=re.IGNORECASE)

                if "IntegerOnly" in rule_name:
                    query = re.sub(r'\bMOD\b', f'MOD({column}, 1)', query, flags=re.IGNORECASE)

                #query = re.sub(r'\bCAST\b', f'CAST({column} AS INTEGER)', query, flags=re.IGNORECASE)

                query = re.sub(r'\b!=\b', '<>', query, flags=re.IGNORECASE)

                # Replace unsupported ~ operator
                if '~' in query:
                    raise ValueError("SQLite does not support the '~' operator. Use LIKE or apply Python regex manually on DataFrame.")

                print(f"Executing SQL query: {query}")

                # Execute the modified query using pandasql
                filtered_df = ps.sqldf(query, locals())
                valid_count = filtered_df.shape[0]
                invalid_count = len(df) - valid_count
                invalid_records = df[~df.index.isin(filtered_df.index)]

            print(f"Rule '{rule_name}' applied on column '{column}'. Valid: {valid_count}, Invalid: {invalid_count} \n")
            return {
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'invalid_records': invalid_records  # Return the DataFrame of invalid records
            }
        
        except Exception as e:
            print(f"#=======>Error applying rule '{rule_name}' on column '{column}': {str(e)}")
            return None  # Return None if there's an error
        
        

    def get_dataset_data(self, dataset):
        selected_data = self.db.get_dataset_by_id(dataset["id"])
        if not selected_data:
            logger.warning(f"No dataset found with ID: {dataset}")
            return None
        logger.info(f"Selected data: {selected_data}")
        s3_datasets = self.dqs.extract_datasets_from_s3_only(selected_data)
        logger.info(f"display s3_datasets: {s3_datasets}")
        if s3_datasets:
            dataset = s3_datasets[0]

            return dataset['dataframe']
        logger.warning("No S3 datasets found")
        return None

    def perform_data_quality_checks(self, df, rule):
        """
        Perform data quality checks on the DataFrame using the rules.
        """

        column = rule.column
        rule_name = rule.rule_name
        sql_script = self.clean_sql_script(rule.query)  # Clean the SQL query
        
        # Check if the column exists in the DataFrame
        if column not in df.columns:
            print(f"Column '{column}' not found in the dataset.")
            
        
        # Check for the presence of JOIN in the SQL script
        if 'JOIN' in sql_script.upper():
            print(f"Skipping rule '{rule_name}' for column '{column}' due to JOIN in query.")

        # Apply the rule and get metrics
        metrics = self.check_rule(df, rule_name, column, sql_script)

        # Only append results if metrics are valid (not None)
        quality_results = {
            'Column': column,
            'Rule': rule_name,
            'Valid Rows': metrics['valid_count'],
            'Incidents': metrics['invalid_count'],
            'Invalid Records': metrics['invalid_records'].to_dict(orient="records")
        }

        return quality_results




    def generate_and_save_quality_report(self, dataset, rule):
        try:
            df = self.get_dataset_data(dataset)

            # Ensure df is a DataFrame, convert if needed
            if isinstance(df, list):
                df = pd.DataFrame(df)

            # Perform data quality checks
            quality_report = self.perform_data_quality_checks(df, rule)

            return quality_report
        except Exception as e:
            logger.error(f"Error in generate_and_save_quality_report: {str(e)}")
            traceback.print_exc()
            return {}


