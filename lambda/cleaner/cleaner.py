import os
import boto3
import time
import json
from boto3.dynamodb.conditions import Key

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get("TABLE_NAME")
DEST_BUCKET = os.environ.get("DEST_BUCKET")
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    print("Cleaner invoked:", json.dumps(event))
    now = int(time.time() * 1000)
    cutoff = now - 10000  # 10 seconds ago (in milliseconds)
    
    # Query DynamoDB using the GSI to find disowned copies older than cutoff.
    response = table.query(
        IndexName="GSI_Disowned",
        KeyConditionExpression=Key("status").eq("disowned") & Key("disownedAt").lte(cutoff)
    )
    items = response.get('Items', [])
    print(f"Found {len(items)} items to clean up.")
    
    for item in items:
        print(f"Deleting copy: {item['copyKey']}")
        # Delete the object from the destination bucket.
        s3.delete_object(Bucket=DEST_BUCKET, Key=item['copyKey'])
        # Remove the record from DynamoDB.
        table.delete_item(
            Key={
                'originalKey': item['originalKey'],
                'copyTimestamp': item['copyTimestamp']
            }
        )
    return {'status': 'cleaned', 'deleted': len(items)}
