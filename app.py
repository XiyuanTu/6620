#!/usr/bin/env python3
import aws_cdk as cdk
# from storage_stack import StorageStack
# from replicator_stack import ReplicatorStack
# from cleaner_stack import CleanerStack
from combined_stack import CombinedStack

app = cdk.App()

# # Create the storage stack with S3 buckets and DynamoDB table.
# storage_stack = StorageStack(app, "StorageStack")

# # Create the Replicator stack and pass references to the storage resources.
# ReplicatorStack(app, "ReplicatorStack",
#     bucket_src=storage_stack.bucket_src,
#     bucket_dst=storage_stack.bucket_dst,
#     table=storage_stack.table
# )

# # Create the Cleaner stack.
# CleanerStack(app, "CleanerStack",
#     bucket_dst=storage_stack.bucket_dst,
#     table=storage_stack.table
# )

CombinedStack(app, "CombinedStack")

app.synth()
