import matplotlib.pyplot as plt
import os
import boto3
import io
import datetime
from boto3.dynamodb.conditions import Key

BUCKET_NAME = os.environ.get("BUCKET_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3_client = boto3.client("s3")

def handler(event, context):
    # Define the time window (last 10 seconds)
    now = datetime.datetime.utcnow()
    ten_seconds_ago = now - datetime.timedelta(seconds=10)
    
    # Query DynamoDB for items in the last 10 seconds.
    response = table.query(
        KeyConditionExpression=Key("bucketName").eq(BUCKET_NAME) & Key("timestamp").between(ten_seconds_ago.isoformat(), now.isoformat())
    )
    items = response.get("Items", [])
    
    # Query the secondary index to retrieve the maximum bucket size ever recorded.
    max_response = table.query(
        IndexName="BucketSizeIndex",
        KeyConditionExpression=Key("bucketName").eq(BUCKET_NAME),
        ScanIndexForward=False,  # Descending order (largest size first)
        Limit=1
    )
    max_items = max_response.get("Items", [])
    max_size = max_items[0]["totalSize"] if max_items else 0

    # Prepare the data for plotting.
    timestamps = []
    sizes = []
    for item in items:
        timestamps.append(datetime.datetime.fromisoformat(item["timestamp"]))
        sizes.append(item["totalSize"])
    
    # Create the plot.
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, sizes, marker="o", label="Bucket Size (Last 10 sec)")
    plt.axhline(y=max_size, color="r", linestyle="--", label="Max Bucket Size")
    plt.xlabel("Timestamp")
    plt.ylabel("Bucket Size (bytes)")
    plt.title("S3 Bucket Size Over Time")
    plt.legend()
    plt.tight_layout()
    
    # Save the plot to an in-memory buffer.
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    
    # Upload the plot image to S3.
    s3_client.put_object(Bucket=BUCKET_NAME, Key="plot.png", Body=buffer, ContentType="image/png")
    
    return {
        "statusCode": 200,
        "body": "Plot created and uploaded to S3 as plot.png"
    }
