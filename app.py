#!/usr/bin/env python3
import aws_cdk as cdk
from notification_stack import NotificationStack
from application_stack import ApplicationStack

app = cdk.App()

# Create the NotificationStack that defines the bucket, DynamoDB table, and size-tracking Lambda
notification_stack = NotificationStack(app, "NotificationStack")

# Create the ApplicationStack that defines the plotting and driver Lambdas.
# Pass only the bucket name (a simple string) and the DynamoDB table construct.
application_stack = ApplicationStack(app, "ApplicationStack",
    bucket_name=notification_stack.bucket.bucket_name,
    history_table=notification_stack.history_table
)

app.synth()
