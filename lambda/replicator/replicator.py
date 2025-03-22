import os
import boto3
import time
import urllib.parse
import json
from boto3.dynamodb.conditions import Key

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get("TABLE_NAME")
DEST_BUCKET = os.environ.get("DEST_BUCKET")
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    for record in event.get('Records', []):
        event_name = record.get('eventName')
        src_bucket = record.get('s3', {}).get('bucket', {}).get('name')
        object_key = record.get('s3', {}).get('object', {}).get('key')
        object_key = urllib.parse.unquote_plus(object_key)
        
        if event_name.startswith('ObjectCreated:'):
            # Handle PUT event
            
            # Query DynamoDB for existing copies.
            response = table.query(
                KeyConditionExpression=Key('originalKey').eq(object_key),
                ScanIndexForward=True  # Ascending order so the oldest copy is first.
            )
            items = response.get('Items', [])
            
            if len(items) >= 3:
                # Delete the oldest copy.
                oldest = items[0]
                print(f"Deleting oldest copy: {oldest['copyKey']}")
                s3.delete_object(Bucket=DEST_BUCKET, Key=oldest['copyKey'])
                table.delete_item(
                    Key={
                        'originalKey': object_key,
                        'copyTimestamp': oldest['copyTimestamp']
                    }
                )
            
            # Create a new copy in the destination bucket.
            timestamp = str(int(time.time() * 1000))
            copy_key = f"{object_key}-{timestamp}"
            print(f"Copying object to: {copy_key}")
            s3.copy_object(
                Bucket=DEST_BUCKET,
                CopySource={'Bucket': src_bucket, 'Key': object_key},
                Key=copy_key
            )
            
            # Insert a new record into DynamoDB.
            table.put_item(
                Item={
                    'originalKey': object_key,
                    'copyTimestamp': timestamp,
                    'copyKey': copy_key,
                    'status': "active"
                }
            )
        
        elif event_name.startswith('ObjectRemoved:'):
            # Handle DELETE event.
            response = table.query(
                KeyConditionExpression=Key('originalKey').eq(object_key)
            )
            items = response.get('Items', [])
            
            for item in items:
                print(f"Marking copy as disowned: {item['copyKey']}")
                table.update_item(
                    Key={
                        'originalKey': object_key,
                        'copyTimestamp': item['copyTimestamp']
                    },
                    UpdateExpression="set #s = :d, disownedAt = :time",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={
                        ":d": "disowned",
                        ":time": int(time.time() * 1000)
                    }
                )
    return {'status': 'done'}
