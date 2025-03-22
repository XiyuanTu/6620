import boto3
import time
import os
import urllib.request  # Make sure to include requests in your driver lambda package

BUCKET_NAME = os.environ.get("BUCKET_NAME")
PLOTTING_API_URL = os.environ.get("PLOTTING_API_URL")

s3_client = boto3.client("s3")

def handler(event, context):
    # Create object assignment1.txt with content "Empty Assignment 1" (19 bytes)
    s3_client.put_object(Bucket=BUCKET_NAME, Key="assignment1.txt", Body="Empty Assignment 1")
    time.sleep(1)
    
    # Update object assignment1.txt with content "Empty Assignment 2222222222" (28 bytes)
    s3_client.put_object(Bucket=BUCKET_NAME, Key="assignment1.txt", Body="Empty Assignment 2222222222")
    time.sleep(1)
    
    # Delete object assignment1.txt
    s3_client.delete_object(Bucket=BUCKET_NAME, Key="assignment1.txt")
    time.sleep(1)
    
    # Create object assignment2.txt with content "33" (2 bytes)
    s3_client.put_object(Bucket=BUCKET_NAME, Key="assignment2.txt", Body="33")
    time.sleep(1)
    
    # Call the plotting lambda via its REST API
    response = urllib.request.urlopen(PLOTTING_API_URL)
    response_body = response.read().decode('utf-8')

    return {
        "statusCode": 200,
        "body": "Driver lambda executed. Plotting API response: " + response_body
    }
