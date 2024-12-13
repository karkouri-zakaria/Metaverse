# DevOps Pipeline for AWS Lambda Management

This repository contains a GitLab CI/CD pipeline for managing AWS Lambda functions. The pipeline includes stages for checking the existence of a Lambda function and deleting associated AWS resources if the function exists.

## Pipeline Stages

1. **check_lambda**: Checks if the specified AWS Lambda function exists.
2. **delete**: Deletes the AWS Lambda function and associated resources if the function exists.

## Variables

The following environment variables are used in the pipeline:

- `AWS_DEFAULT_REGION`: AWS region where the Lambda function is deployed (default: `us-east-1`).
- `LAMBDA_FUNCTION_NAME`: Name of the Lambda function to check and delete.
- `LAMBDA_EXISTS`: Flag to indicate if the Lambda function exists (default: `false`).

## Usage

### Prerequisites

- AWS CLI with appropriate permissions to manage Lambda functions, IAM roles, KMS keys, and Secrets Manager.
- GitLab runner with Docker executor.
- Create two S3 buckets named datacon-buck and quality-rules (for test cases)
- Upload to files to your bucket **empty.xlsx** and **third.csv** (for test cases)

### Getting started

- Clone the repository and change the directory to the project folder:

```bash
git clone https://gitlab.com/cloud-science/ms-dataquality-p.git
cd ms-dataquality-p
```

### How to Start the FastAPI Application

- Before installing dependencies, create a virtual environment to avoid conflicts with global packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

- Install the dependencies and required packages:

```bash
pip install -r requirements.txt
```

- Run FastAPI Start the FastAPI server by running the following command:

```bash
# In the first terminal
python api/DataConnectAPIs.py

# In the second terminal
python api/DataQualityAPIs.py
```

## DataConnect API Service (Port 1001)
### Available APIs for DataConnect

#### 1. **Connect to AWS S3 / Google Drive :**

##### a. Description

This endpoint allows users to connect to their AWS S3 or Google Drive accounts. By providing the necessary credentials and details in the request body, users can retrieve a list of buckets or folders available in their specified cloud storage instance.

> **Note:** This endpoint triggers the pipeline to create all necessary AWS services.

##### b. Example Usage with 'aws s3'

- **Method:** POST
- **URL:** `http://localhost:1001/api/data-connect/create/get-buckets-folders`
- **Request body (JSON):**

```json
{
  "user_id": "your-user-id",
  "user_id_variable": "admin",
  "instance_id": "456168984",
  "instance_type": "s3",
  "workspace_id": "your-workspace-id",
  "region": "us-east-1",
  "key": "your-aws-access-key",
  "aws_secret_access_key": "your-aws-secret-access-key"
}
```

#### 2. **Get bucket's/folder's files :**

##### a. Description

This endpoint retrieves the list of files from a specified S3 bucket or google drive folder.

> **Note:** This endpoint depends on the first endpoint, as it requires the Lambda function to be deployed in order to retrieve files from the provided source.

##### b. Example Usage with 'aws s3'

- **Method:** POST
- **URL:** `http://localhost:1001/api/data-connect/files`
- **Request body (JSON):**

```json
{
  "user_id": "your-user-id",
  "user_id_variable": "admin",
  "instance_type": "s3",
  "instance_id": "456168984",
  "source_name": "datacon-buck" // your S3 bucket name
}
```

> **Note:** The `user_id_variable` property is optional for now as it is not currently utilized in the function of the endpoint.

#### 3. **Create Dataconnect instance :**

##### a. Description

This endpoint allows users to create a new Dataconnect instance. It need to provide details such as user ID, user variable (user Type: "admin" or "user"), instance ID, instance type, workspace ID, AWS credentials, and information about the data sources and datasets.

##### b. Example Usage with 'aws s3'

- **Method:** POST
- **URL:** `http://localhost:1001/api/data-connect/create-instance`
- **Request body (JSON):**

```json
{
  "user_id": "your-user-id",
  "user_id_variable": "admin",
  "instance_type": "s3",
  "instance_id": "456168984",
  "workspace_id": "your-workspace-id",
  "region": "us-east-1",
  "key": "your-aws-access-key",
  "aws_secret_access_key": "your-aws-secret-access-key",
  "datasources": [
    {
      "name": "datacon-buck",
      "datasets": [
        {
          "name": "empty.xlsx",
          "connexion_status": "active",
          "dataset_type": "excel",
          "last_scan": "2024-10-17T08:58:10+00:00"
        },
        {
          "name": "third.csv",
          "connexion_status": "active",
          "dataset_type": "csv",
          "last_scan": "2024-10-17T10:41:19+00:00"
        }
      ]
    },
    {
      "name": "offboard_buck",
      "datasets": [
        {
          "name": "offboarding.tf",
          "connexion_status": "active",
          "dataset_type": "terraform",
          "last_scan": "2024-10-16T10:47:33+00:00"
        }
      ]
    }
  ]
}
```

#### 4. **Get Users Instances :**

##### a. Description

This endpoint retrieves instances associated with a specific user and workspace. By providing the user_id and workspace_id as path parameters.

##### b. Example Usage with 'aws s3'

- **Method:** GET
- **URL:** `http://localhost:1001/api/data-connect/instances/:user_id/:workspace_id`

###### Parameters

- `a0121d49-887e-4999-b00f` (path parameter): The ID of the user.
- `f1563248-d0be-443b-ad29` (path parameter): The ID of the workspace.

###### Example Response

```json
{
  "dataconnect_id": "23b2a52f-d79a-4296-9345",
  "user_id": "a0121d49-887e-4999-b00f",
  "user_id_variable": "admin",
  "instance_type": "s3",
  "instance_id": "456168984",
  "workspace_id": "f1563248-d0be-443b-ad29",
  "region": "us-east-1",
  "secret_key": "+C33N0ch0NH3pYwvjdKJ87GF+Dvsd98-Fh",
  "key": "IAM4YOUZ78DE9SIFTYY6TLAKOM"
}
```

#### 5. **Get instance's bucket/folders :**

##### a. Description

This endpoint retrieves the bucket or folders associated with a specific instance. By providing the instance_id as a path parameter, it return the details of the instance's bucket or folders (for now just `name`).

##### b. Example Usage with 'aws s3'

- **Method:** GET
- **URL:** `http://localhost:1001/api/data-connect/get-sources/:instance_id`

###### Parameters

- `456168984` (path parameter): The ID of the instance.

###### Example Response

```json
{
  "id": "23b73235-ffed-4104-9397-07a4d4e88f3e",
  "name": "datacon-buck",
  "instance_id": "456168984"
}
```

#### 6. Delete script triggering Dataconnect instance:

- **Method** DELETE
- **URL:** `http://localhost:1001/api/data-connect/delete`
- **Request body (JSON):**

```json
{
  "creds": {
    "aws_access_key_id": "your-aws-access-key",
    "aws_secret_access_key": "your-aws-secret-access-key",
    "region": "us-east-1"
  },
  "resources": {
    "user_id": "instance-user-id",
    "instance_id": "instance-given-id",
    "instance_type": "instance-type",
    "id": "instance-table-id"
  }
}
```

#### 7. **Create default user + workspaces (test cases only):**

- **Method:** GET
- **URL:** `http://localhost:1001/db/init`

## DataQuality API Service (Port 1002)
### Available APIs for DataQuality

#### 1. Add Data Quality Rules:

- **Method** POST
- **URL:** `http://localhost:1002/api/data-quality/rules`
- **Request body (JSON):**

```json
{
    "id": "your-dataset-id", 
    "name": "third.csv"
}
```

#### 2. Perform Quality Check on Dataset:

- **Method** POST
- **URL:** `http://localhost:1002/api/data-quality/dataset/apply-check`
- **Request body (JSON):**

```json
{
    "type": "sql",
    "name": "test-check",
    "description": "this is a test check.",
    "rule": {
        "column": "selected-column", 
        "rule_name": "rule-name", 
        "query": "rule-query" 
    },
    "dataset": {
        "id": "dataset-id", 
        "name": "third.csv"
    }
}
```

## AWS Services Used

This project leverages the following AWS services:

- AWS Lambda
- AWS S3
- AWS DynamoDB
- AWS ECR
- AWS EC2
- AWS Secrets Manager
- AWS IAM
- AWS KMS

## API Deployment on AWS EC2

This section covers how to deploy the FastAPI application on an AWS EC2 instance, configure it to expose the necessary ports, install Docker, and run the application inside a Docker container.

#### 1. Launch an EC2 Instance

- Open the [AWS EC2 Console](https://aws.amazon.com/ec2/) and launch a new instance.
- Choose the appropriate AMI (e.g., Ubuntu) and instance type (e.g., `t2.micro` for free tier).
- In **Security Group** settings, add a custom TCP rule to allow traffic on port `1001-1002`:
  - **Type**: Custom TCP Rule
  - **Port Range**: `1001-1002`
  - **Source**: `0.0.0.0/0` (or limit it to specific IPs for better security)

#### 2. Install Docker on EC2

After connecting to the instance, install Docker by running the following commands:

```bash
# Update and install prerequisites
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's GPG key and repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list and install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Enable Docker and add your user to the Docker group (optional)
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

You may need to log out and log back in for the group changes to take effect.

#### 3. Create and Run the Docker Cluster

To deploy your services on an EC2 instance, follow these steps to set up and run a Docker Compose cluster using a `docker-compose.yaml` file:

1. Prepare the Docker Compose File: Create a docker-compose.yaml file with the following content:

```bash
version: '3.8'

services:
  dataconnect-api:
    image: <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/dataconnect-api:latest
    container_name: dataconnect-api
    ports:
      - "1001:1001"

  dataquality-api:
    image: <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/dataquality-api:latest
    container_name: dataquality-api
    ports:
      - "1002:1002"
```
Replace <AWS_ACCOUNT_ID> and <AWS_REGION> with your actual AWS account ID and region.

2. Login to AWS ECR (if required):

```bash
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
```

3. Run the Docker Compose Cluster:

In the same directory as your `docker-compose.yaml` file, run the following command to start both services:

```bash
docker-compose up -d
```
This will create and run a cluster containing both the `dataconnect-api` and `dataquality-api` services on ports 1001 and 1002, respectively.

#### 4. Verify Deployment

Your FastAPI application should now be running on ports **1001** for Data-connect service and **1002** for Data-quality service of your EC2 instance. You can verify this by visiting:

- http://your-ec2-public-ip:1001
- http://your-ec2-public-ip:1002

You should see your FastAPI application up and running.
