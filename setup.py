import boto3
import botocore
import time

def create_s3_bucket(bucket_name, region='us-east-1'):
    s3 = boto3.client('s3', region_name=region)
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists.")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            if region == 'us-east-1':
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(Bucket=bucket_name,
                                 CreateBucketConfiguration={'LocationConstraint': region})
            print(f"Bucket {bucket_name} created.")
        else:
            raise

def create_dynamodb_table(table_name, region='us-east-1'):
    dynamodb = boto3.client('dynamodb', region_name=region)
    try:
        dynamodb.describe_table(TableName=table_name)
        print(f"Table {table_name} already exists.")
    except dynamodb.exceptions.ResourceNotFoundException:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'BucketName', 'KeyType': 'HASH'},
                {'AttributeName': 'Timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'BucketName', 'AttributeType': 'S'},
                {'AttributeName': 'Timestamp', 'AttributeType': 'N'},
                {'AttributeName': 'TotalSize', 'AttributeType': 'N'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'MaxSizeIndex',
                    'KeySchema': [
                        {'AttributeName': 'BucketName', 'KeyType': 'HASH'},
                        {'AttributeName': 'TotalSize', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ]
        )
        print(f"Creating table {table_name}...")
        dynamodb.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Table {table_name} created.")
        
if __name__ == '__main__':
    BUCKET_NAME = "testbucket-xiyuan-6620-hw2"
    TABLE_NAME = "S3-object-size-history"
    REGION = 'us-east-1'
    
    create_s3_bucket(BUCKET_NAME, region=REGION)
    create_dynamodb_table(TABLE_NAME, region=REGION)
