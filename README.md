awslocal s3api create-bucket --bucket datacon-buck

awslocal s3 cp "C:\Users\zakar\Desktop\dataset.csv" s3://datacon-buck/

awslocal s3 cp "lambda-docker-s3-bucket\lambda_function.zip" s3://handlers/ 	

awslocal s3api list-buckets

awslocal iam list-users

awslocal dynamodb list-tables

awslocal dynamodb scan --table-name <table_name> --limit 5

awslocal dynamodb describe-table --table-name <table_name>

awslocal dynamodb put-item --table-name users --item "{\"id\": {\"S\": \"1\"}, \"username\": {\"S\": \"john_doe\"}}"

awslocal dynamodb scan --table-name users

awslocal secretsmanager delete-secret --secret-id "1e93d071-da24-4190-b92b-009cca152182_0da1ce94-e9c7-4d09-a43e-064d59fb1f6f_credentials_secret" --force-delete-without-recovery

awslocal lambda update-function-code --function-name "27166a88-c4df-4b49-a9b3-e2250eae544c_s3_lambda" --zip-file fileb://lambda-docker-s3-bucket\lambda_function.zip --environment "Variables={INSTANCE_ID=27166a88-c4df-4b49-a9b3-e2250eae544c,SECRET_NAME=13c33294-cf52-452e-9f20-4dde9a77b218_27166a88-c4df-4b49-a9b3-e2250eae544c_credentials_secret,INSTANCE_TYPE=s3,USER_ID=13c33294-cf52-452e-9f20-4dde9a77b218}"

aws lambda invoke --function-name "27166a88-c4df-4b49-a9b3-e2250eae544c_s3_lambda" --payload '{"user_id": "13c33294-cf52-452e-9f20-4dde9a77b218", "instance_id": "27166a88-c4df-4b49-a9b3-e2250eae544c", "instance_type": "s3", "operation": "list_files", "bucket_name": "datacon-buck"}' response.json
aws lambda invoke --function-name "27166a88-c4df-4b49-a9b3-e2250eae544c_s3_lambda" \
--payload file://payload.json \
response.json

awslocal secretsmanager update-secret --secret-id "13c33294-cf52-452e-9f20-4dde9a77b218_27166a88-c4df-4b49-a9b3-e2250eae544c_credentials_secret" --secret-string file://./keys.json 

awslocal lambda get-function-configuration --function-name "27166a88-c4df-4b49-a9b3-e2250eae544c_s3_lambda" 


awslocal lambda list-functions
awslocal kms list-keys
awslocal ecr describe-repositories

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

terraform apply -auto-approve
