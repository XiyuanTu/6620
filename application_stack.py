from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    Duration
)
from constructs import Construct

class ApplicationStack(Stack):
    def __init__(self, scope: Construct, id: str, bucket_name: str, history_table, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create a Lambda Layer for matplotlib.
        matplotlib_layer = _lambda.LayerVersion(self, "MatplotlibLayer",
            code=_lambda.Code.from_asset("lambda_layers/matplotlib_layer.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11]
        )
        
        # Plotting Lambda: uses matplotlib to generate a plot and uploads it to S3.
        self.plotting_lambda = _lambda.Function(self, "PlottingLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda_functions/plotting"),
            layers=[matplotlib_layer],
            environment={
                "BUCKET_NAME": bucket_name,
                "TABLE_NAME": history_table.table_name
            },
            timeout=Duration.seconds(30)
        )
        # Grant the plotting lambda read access to the DynamoDB table.
        history_table.grant_read_data(self.plotting_lambda)       
        
        # Grant S3 full access by attaching the managed policy.
        self.plotting_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )

        # Grant DynamoDB full access.
        self.plotting_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )

        # Expose the plotting lambda via an API Gateway REST API.
        api = apigw.LambdaRestApi(self, "PlottingApi",
            handler=self.plotting_lambda,
            proxy=False
        )
        plot_resource = api.root.add_resource("plot")
        plot_resource.add_method("GET")
        
        # Driver Lambda: simulates S3 operations and calls the plotting API.
        self.driver_lambda = _lambda.Function(self, "DriverLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda_functions/driver"),
            environment={
                "BUCKET_NAME": bucket_name,
                "PLOTTING_API_URL": api.url + "plot"
            },
            timeout=Duration.seconds(30)
        )

        # Add inline policy to allow PutObject and DeleteObject on the bucket.
        self.driver_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:DeleteObject"],
                resources=[f"arn:aws:s3:::{bucket_name}/*"]
            )
        )
