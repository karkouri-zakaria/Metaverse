from pyspark.sql import SparkSession
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#load_dotenv()

env_file = '.env'
load_dotenv(env_file, override=True)

def create_spark_session():
    try:
        spark_s3 = SparkSession.builder \
            .appName("S3DataReader") \
            .config("spark.master", "local[*]") \
            .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.2.0,com.amazonaws:aws-java-sdk-bundle:1.11.563,com.crealytics:spark-excel_2.11:0.13.5") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
            .config("spark.hadoop.fs.s3a.access.key", os.getenv('ACCESS_KEY')) \
            .config("spark.hadoop.fs.s3a.secret.key", os.getenv('SECRET_KEY')) \
            .config("spark.hadoop.fs.s3a.endpoint", f"s3.{os.getenv('AWS_REGION')}.amazonaws.com") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.com.amazonaws.services.s3.enableV4", "true") \
            .getOrCreate()
        logger.info("SparkSession created successfully in local mode")
        return spark_s3
    except Exception as e:
        logger.error(f"Failed to create SparkSession: {e}")
        raise

""" spark = create_spark_session()

bucket_name = "saas-bucket-1111"
file_name = f"sales_data_sample.csv"

s3_path = f"s3a://{bucket_name}/{file_name}" """

# Test S3 connection
""" try:
    #spark._jsc.hadoopConfiguration().set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    #spark._jsc.hadoopConfiguration().set("com.amazonaws.services.s3.enableV4", "true")
    #spark._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
    
    # List files in the bucket
    file_list = spark._jsc.textFile(f"s3a://{bucket_name}/").collect()
    logger.info(f"Files in bucket: {file_list}")
except Exception as e:
    logger.error(f"Error testing S3 connection: {e}") """

""" try:
    df = spark.read.csv(s3_path, header=True, inferSchema=True)
    df.show()

except Exception as e:
    logger.error(f"Error reading dataset {s3_path}: {str(e)}") """


""" def create_spark_session():
    try:
        spark = SparkSession.builder \
            .appName("DataQualityApp") \
            .config("spark.master", "local[*]") \
            .config("spark.driver.bindAddress", "0.0.0.0") \
            .config("spark.ui.port", "4041") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .getOrCreate()

        logger.info("SparkSession created successfully in local mode")
        return spark
    except Exception as e:
        logger.error(f"Failed to create SparkSession: {e}")
        raise """

""" def create_spark_session():
    # Set the local IP address
    os.environ['SPARK_LOCAL_IP'] = '192.168.145.5'  # Use the IP address from the warning

    spark = SparkSession.builder \
        .appName("DataQualityService") \
        .config("spark.master", "spark://localhost:7077") \
        .config("spark.driver.host", "192.168.145.5") \
        .config("spark.driver.bindAddress", "0.0.0.0") \
        .config("spark.ui.port", "4041") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()

    return spark """

# Use this function to create your Spark session
"""spark = create_spark_session()

# Test the connection
try:
    df = spark.createDataFrame([(1, "test")], ["id", "name"])
    print("Successfully created a DataFrame:")
    df.show()
except Exception as e:
    print(f"Failed to create DataFrame: {str(e)}")

# Don't forget to stop the session when you're done
spark.stop()"""