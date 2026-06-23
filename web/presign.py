"""
S3 presigned URL generation and upload status checks for the CDAR upload portal.

AWS credentials are resolved via the standard boto3 chain:
  env vars (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
  → ~/.aws/credentials
  → EC2/ECS instance role

S3 bucket CORS must allow PUT from the portal origin:
  AllowedMethods: [PUT]
  AllowedOrigins: [https://your-portal-domain.com]
  AllowedHeaders: [*]
  ExposeHeaders:  [ETag]
"""

import boto3
from botocore.exceptions import ClientError


def extract_s3_key(prefix: str) -> str:
    return f"{prefix.rstrip('/')}/extract.tar.gz"


def generate_presigned_put(
    bucket: str,
    prefix: str,
    region: str,
    expiry: int = 172800,
) -> str:
    key = extract_s3_key(prefix)
    s3 = boto3.client("s3", region_name=region)
    return s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": bucket,
            "Key": key,
            "ContentType": "application/octet-stream",
        },
        ExpiresIn=expiry,
    )


def check_upload_exists(bucket: str, prefix: str, region: str) -> bool:
    key = extract_s3_key(prefix)
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise
