# Dockerfile

# pull official base image
FROM amazon/aws-lambda-python:3.8

# Copy function code and requirements
#COPY function.py ${LAMBDA_TASK_ROOT}

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install any dependencies
RUN pip install -r requirements.txt

# Set the CMD to your handler (without file extension)
#CMD ["function.lambda_handler"]
CMD ["lambda_function.lambda_handler"]