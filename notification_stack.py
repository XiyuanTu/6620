from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    RemovalPolicy,
    aws_iam as iam,
    Duration
)
from aws_cdk.aws_s3_notifications import LambdaDestination
from constructs import Construct

class NotificationStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create S3 bucket (no hardcoded name)
        self.bucket = s3.Bucket(self, "DataBucket")
        
        # Create DynamoDB table to store S3 bucket size history
        self.history_table = dynamodb.Table(self, "S3ObjectSizeHistory",
            partition_key=dynamodb.Attribute(name="bucketName", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY  # (Use caution in production)
        )
        
        # Add a Global Secondary Index to support queries on total size
        self.history_table.add_global_secondary_index(
            index_name="BucketSizeIndex",
            partition_key=dynamodb.Attribute(name="bucketName", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="totalSize", type=dynamodb.AttributeType.NUMBER)
        )
        
        # Create Size-Tracking Lambda in the same stack
        self.size_tracking_lambda = _lambda.Function(self, "SizeTrackingLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda_functions/size_tracking"),
            environment={
                "BUCKET_NAME": self.bucket.bucket_name,
                "TABLE_NAME": self.history_table.table_name
            },
            timeout=Duration.seconds(30)
        )
        
        # Grant permissions: allow lambda to read from the bucket and write to DynamoDB.
        self.bucket.grant_read(self.size_tracking_lambda)
        self.history_table.grant_write_data(self.size_tracking_lambda)
        
        # Configure bucket event notifications for object creation and removal.
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            LambdaDestination(self.size_tracking_lambda)
        )
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_REMOVED,
            LambdaDestination(self.size_tracking_lambda)
        )
