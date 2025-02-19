import boto3
import json
import time

# AWS Clients using root credentials (assumed to have IAM permissions)
iam_client = boto3.client("iam")
sts_client = boto3.client("sts")

# ---------------------- 1. CREATE IAM ROLES ----------------------
def create_role(role_name, policy_document):
    try:
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(policy_document),
            Description=f"{role_name} Role",
        )
        print(f"✅ Created IAM Role: {role_name}")
        return response["Role"]["Arn"]
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"⚠️ Role {role_name} already exists")
        return iam_client.get_role(RoleName=role_name)["Role"]["Arn"]

# Trust policy (Allows any IAM principal in the account to assume the role)
assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": "sts:AssumeRole",
        }
    ],
}

dev_role_arn = create_role("Dev", assume_role_policy)
user_role_arn = create_role("User", assume_role_policy)

# ---------------------- 2. ATTACH IAM POLICIES ----------------------
dev_policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
user_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket", "s3:GetObject"],
            "Resource": ["arn:aws:s3:::*"],
        },
    ],
}

def attach_policy(role_name, policy_arn=None, policy_json=None):
    if policy_arn:
        iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"✅ Attached managed policy to {role_name}")
    elif policy_json:
        policy_response = iam_client.create_policy(
            PolicyName=f"{role_name}Policy", PolicyDocument=json.dumps(policy_json)
        )
        iam_client.attach_role_policy(
            RoleName=role_name, PolicyArn=policy_response["Policy"]["Arn"]
        )
        print(f"✅ Attached inline policy to {role_name}")

attach_policy("Dev", policy_arn=dev_policy_arn)
attach_policy("User", policy_json=user_policy)

# ---------------------- 3. CREATE IAM USER & ACCESS KEYS ----------------------
user_name = "CustomS3User"
try:
    iam_client.create_user(UserName=user_name)
    print(f"✅ Created IAM User: {user_name}")
except iam_client.exceptions.EntityAlreadyExistsException:
    print(f"⚠️ User {user_name} already exists")

# Attach permissions to allow the user to assume roles
iam_client.put_user_policy(
    UserName=user_name,
    PolicyName="AssumeRolePolicy",
    PolicyDocument=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": [dev_role_arn, user_role_arn],
                }
            ],
        }
    ),
)

# Create access keys for the user
access_keys = iam_client.create_access_key(UserName=user_name)["AccessKey"]
custom_s3_access_key = access_keys["AccessKeyId"]
custom_s3_secret_key = access_keys["SecretAccessKey"]
print(f"✅ custom_s3_access_key: {custom_s3_access_key}")
print(f"✅ custom_s3_secret_key: {custom_s3_secret_key}")
time.sleep(10)

# ---------------------- 4. ASSUME DEV ROLE USING CREATED USER ----------------------
def assume_role(role_arn, user_access_key, user_secret_key):
    """Assumes a role using the created IAM user."""
    temp_sts_client = boto3.client(
        "sts",
        aws_access_key_id=user_access_key,
        aws_secret_access_key=user_secret_key,
    )
    assumed_role = temp_sts_client.assume_role(RoleArn=role_arn, RoleSessionName="TempSession")
    credentials = assumed_role["Credentials"]
    return boto3.client(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

# Assume Dev role explicitly using the created user’s credentials
dev_s3 = assume_role(dev_role_arn, custom_s3_access_key, custom_s3_secret_key)

bucket_name = "xiyuan-6620-hw1"
try:
    dev_s3.create_bucket(Bucket=bucket_name)
    print(f"✅ Created bucket: {bucket_name}")
except Exception as e:
    print(f"❌ Bucket creation failed: {e}")

# Upload files
files = {
    "assignment1.txt": "Empty Assignment 1",
    "assignment2.txt": "Empty Assignment 2",
}
for filename, content in files.items():
    dev_s3.put_object(Bucket=bucket_name, Key=filename, Body=content)
    print(f"✅ Uploaded {filename}")

# Upload image
image_path = "img.jpg"  # Replace with a valid image path
with open(image_path, "rb") as img:
    dev_s3.put_object(Bucket=bucket_name, Key="recording1.jpg", Body=img)
    print("✅ Uploaded recording1.jpg")

# ---------------------- 5. ASSUME USER ROLE USING CREATED USER ----------------------
user_s3 = assume_role(user_role_arn, custom_s3_access_key, custom_s3_secret_key)

# List objects with "assignment" prefix
response = user_s3.list_objects_v2(Bucket=bucket_name, Prefix="assignment")
total_size = sum(obj["Size"] for obj in response.get("Contents", []))
print(f"📊 Total size of objects with 'assignment' prefix: {total_size} bytes")

# # ---------------------- 6. ASSUME DEV ROLE AGAIN TO DELETE EVERYTHING ----------------------
dev_s3 = assume_role(dev_role_arn, custom_s3_access_key, custom_s3_secret_key)

# Delete all objects
objects = dev_s3.list_objects_v2(Bucket=bucket_name).get("Contents", [])
for obj in objects:
    dev_s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
    print(f"🗑️ Deleted {obj['Key']}")

# Delete bucket
dev_s3.delete_bucket(Bucket=bucket_name)
print(f"🗑️ Deleted bucket: {bucket_name}")
