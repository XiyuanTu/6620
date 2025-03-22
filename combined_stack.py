from aws_cdk import (
    App,
    Stack,
    RemovalPolicy,
    Duration
)
from constructs import Construct
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets

class CombinedStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create the source bucket.
        self.bucket_src = s3.Bucket(self, "BucketSrc",
            bucket_name="6620-midterm-txy-src-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # Create the destination bucket.
        self.bucket_dst = s3.Bucket(self, "BucketDst",
            bucket_name="6620-midterm-txy-dst-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # Create the DynamoDB table with a composite primary key.
        self.table = dynamodb.Table(self, "TableT",
            partition_key=dynamodb.Attribute(name="originalKey", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="copyTimestamp", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Add a Global Secondary Index (GSI) to query disowned copies.
        self.table.add_global_secondary_index(
            index_name="GSI_Disowned",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="disownedAt", type=dynamodb.AttributeType.NUMBER),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Create the Replicator Lambda function.
        replicator_lambda = _lambda.Function(self, "ReplicatorLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="replicator.handler",
            code=_lambda.Code.from_asset("lambda/replicator"),
            environment={
                "TABLE_NAME": self.table.table_name,
                "DEST_BUCKET": self.bucket_dst.bucket_name
            }
        )
        
        # Grant necessary permissions for the Replicator Lambda.
        self.table.grant_read_write_data(replicator_lambda)
        self.bucket_dst.grant_write(replicator_lambda)
        self.bucket_src.grant_read(replicator_lambda)
        
        # Configure the source bucket to trigger the Replicator Lambda.
        self.bucket_src.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(replicator_lambda)
        )
        self.bucket_src.add_event_notification(
            s3.EventType.OBJECT_REMOVED,
            s3n.LambdaDestination(replicator_lambda)
        )
        
        # Create the Cleaner Lambda function.
        cleaner_lambda = _lambda.Function(self, "CleanerLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="cleaner.handler",
            code=_lambda.Code.from_asset("lambda/cleaner"),
            environment={
                "TABLE_NAME": self.table.table_name,
                "DEST_BUCKET": self.bucket_dst.bucket_name
            },
            timeout=Duration.minutes(2)  # Cleaner runs for up to 2 minute.
        )
        
        # Grant permissions to the Cleaner Lambda.
        self.table.grant_read_write_data(cleaner_lambda)
        self.bucket_dst.grant_read_write(cleaner_lambda)

        # Schedule the Cleaner Lambda to run every 1 min.
        rule = events.Rule(self, "CleanerScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(1))
        )
        rule.add_target(targets.LambdaFunction(cleaner_lambda))