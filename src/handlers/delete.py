import json
import boto3
import time
from botocore.exceptions import ClientError

iam_client = boto3.client("iam")

def detach_managed_policies(role_name):
    """ 移除所有附加的 Managed Policies """
    try:
        paginator = iam_client.get_paginator("list_attached_role_policies")
        for page in paginator.paginate(RoleName=role_name):
            for policy in page.get("AttachedPolicies", []):
                policy_arn = policy["PolicyArn"]
                try:
                    iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                    print(f"Detached managed policy {policy_arn} from {role_name}")
                    time.sleep(0.2)  # 避免 AWS API 限制
                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchEntity":
                        print(f"Policy {policy_arn} already detached.")
                    else:
                        print(f"Error detaching policy {policy_arn}: {e}")
    except Exception as e:
        print(f"Error detaching managed policies from {role_name}: {e}")

def delete_inline_policies(role_name):
    """ 刪除所有內嵌政策 (Inline Policies) """
    try:
        paginator = iam_client.get_paginator("list_role_policies")
        for page in paginator.paginate(RoleName=role_name):
            for policy_name in page.get("PolicyNames", []):
                try:
                    iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
                    print(f"Deleted inline policy {policy_name} from {role_name}")
                    time.sleep(0.2)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchEntity":
                        print(f"Inline policy {policy_name} already deleted.")
                    else:
                        print(f"Error deleting inline policy {policy_name}: {e}")
    except Exception as e:
        print(f"Error deleting inline policies from {role_name}: {e}")

def remove_instance_profiles(role_name):
    """ 移除角色與 Instance Profile 的綁定 """
    try:
        response = iam_client.list_instance_profiles_for_role(RoleName=role_name)
        for profile in response.get("InstanceProfiles", []):
            profile_name = profile["InstanceProfileName"]
            try:
                iam_client.remove_role_from_instance_profile(
                    InstanceProfileName=profile_name, RoleName=role_name
                )
                print(f"Removed role {role_name} from instance profile {profile_name}")
                time.sleep(0.2)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchEntity":
                    print(f"Instance profile {profile_name} not found.")
                else:
                    print(f"Error removing instance profile {profile_name}: {e}")
    except Exception as e:
        print(f"Error listing instance profiles for {role_name}: {e}")

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    try:
        for record in event.get("Records", []):
            if record["eventName"] == "REMOVE":  # 只處理 DynamoDB 刪除事件
                old_image = record.get("dynamodb", {}).get("OldImage", {})

                # 取得 Role Name
                role_name = old_image.get("role_name", {}).get("S")
                if not role_name:
                    print("No role_name found, skipping.")
                    continue

                print(f"Processing IAM Role: {role_name}")

                # 解除角色附加的管理政策
                detach_managed_policies(role_name)

                # 刪除角色的內嵌政策
                delete_inline_policies(role_name)

                # 移除 Instance Profile 綁定
                remove_instance_profiles(role_name)

                # 刪除 IAM Role
                try:
                    iam_client.delete_role(RoleName=role_name)
                    print(f"IAM Role {role_name} deleted successfully.")
                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchEntity":
                        print(f"IAM Role {role_name} does not exist.")
                    else:
                        print(f"Error deleting IAM Role {role_name}: {e}")

        return {"statusCode": 200, "body": "Processing complete"}

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"statusCode": 500, "body": f"Internal server error: {e}"}
