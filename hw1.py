import boto3
import json
import time

iam = boto3.client('iam')
sts = boto3.client('sts')
s3 = boto3.client('s3')

DEV_ROLE = "Dev"
USER_ROLE = "User"

BUCKET_NAME = "xiyuan-tu-assignment-1"

FILES = {
    "assignment1.txt": "Empty Assignment 1",
    "assignment2.txt": "Empty Assignment 2",
    "img.jpg": r"C:\Users\75958\6620\HW1\img.jpg"
}


def create_iam_role(role_name, policy_document):
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(policy_document)
        )
        print(f"IAM Role {role_name} created.")
        return role['Role']['Arn']
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM Role {role_name} already exists.")
        return iam.get_role(RoleName=role_name)['Role']['Arn']

def attach_policy_to_role(role_name, policy_arn):
    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    print(f"Policy {policy_arn} attached to {role_name}.")

def create_iam_user(user_name):
    try:
        iam.create_user(UserName=user_name)
        print(f"IAM User {user_name} created.")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM User {user_name} already exists.")


def assume_role(role_arn):
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="AssumeRoleSession"
    )
    return response['Credentials']


def create_s3_bucket(bucket_name):
    s3.create_bucket(Bucket=bucket_name)
    print(f"S3 bucket {bucket_name} created.")


def upload_files(bucket_name, files):
    for filename, content in files.items():
        if filename.endswith(".txt"):
            s3.put_object(Bucket=bucket_name, Key=filename, Body=content)
        else:
            with open(content, "rb") as file:
                s3.upload_fileobj(file, bucket_name, filename)
        print(f"Uploaded {filename} to {bucket_name}.")


def list_objects_with_prefix(bucket_name, prefix):
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    total_size = sum(obj['Size'] for obj in response.get('Contents', []))
    print(f"Total size of objects with prefix '{prefix}': {total_size} bytes")


def delete_bucket_and_objects(bucket_name):
    response = s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        for obj in response['Contents']:
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            print(f"Deleted {obj['Key']} from {bucket_name}.")
    s3.delete_bucket(Bucket=bucket_name)
    print(f"Deleted S3 bucket {bucket_name}.")


trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::697816050693:user/AdminUser"},
            "Action": "sts:AssumeRole"
        }
    ]
}

dev_policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
user_policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

# Step 1: Create IAM Roles
dev_role_arn = create_iam_role(DEV_ROLE, trust_policy)
user_role_arn = create_iam_role(USER_ROLE, trust_policy)

# Step 2: Attach Policies to Roles
attach_policy_to_role(DEV_ROLE, dev_policy_arn)
attach_policy_to_role(USER_ROLE, user_policy_arn)

# Step 3: Assume Dev Role and Perform S3 Operations
dev_credentials = assume_role(dev_role_arn)
s3 = boto3.client('s3',
                  aws_access_key_id=dev_credentials['AccessKeyId'],
                  aws_secret_access_key=dev_credentials['SecretAccessKey'],
                  aws_session_token=dev_credentials['SessionToken'])

create_s3_bucket(BUCKET_NAME)
upload_files(BUCKET_NAME, FILES)

# Step 4: Assume User Role and Compute Assignment File Sizes
user_credentials = assume_role(user_role_arn)
s3 = boto3.client('s3',
                  aws_access_key_id=user_credentials['AccessKeyId'],
                  aws_secret_access_key=user_credentials['SecretAccessKey'],
                  aws_session_token=user_credentials['SessionToken'])

list_objects_with_prefix(BUCKET_NAME, "assignment")

# Step 5: Assume Dev Role Again to Delete Bucket and Objects
dev_credentials = assume_role(dev_role_arn)
s3 = boto3.client('s3',
                  aws_access_key_id=dev_credentials['AccessKeyId'],
                  aws_secret_access_key=dev_credentials['SecretAccessKey'],
                  aws_session_token=dev_credentials['SessionToken'])

delete_bucket_and_objects(BUCKET_NAME)

print("Script execution completed.")
