import boto3
import os
import datetime

BUCKET_NAME = os.environ.get("BUCKET_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    # List all objects in the bucket and compute the total size and count.
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    total_size = 0
    object_count = 0
    
    if "Contents" in response:
        for obj in response["Contents"]:
            total_size += obj["Size"]
            object_count += 1
    
    # Record the current timestamp in ISO format.
    timestamp = datetime.datetime.utcnow().isoformat()
    
    # Write the size info to the DynamoDB table.
    table.put_item(
        Item={
            "bucketName": BUCKET_NAME,
            "timestamp": timestamp,
            "totalSize": total_size,
            "objectCount": object_count
        }
    )
    
    return {
        "statusCode": 200,
        "body": "Size tracking updated."
    }
