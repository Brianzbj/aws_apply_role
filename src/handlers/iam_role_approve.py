import boto3
import json

dynamodb = boto3.client("dynamodb")
iam = boto3.client("iam")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # 取得 API Gateway 的 GET 參數
        params = event.get("queryStringParameters", {})

        request_id = params.get("request_id")
        action = params.get("action")

        if not request_id or not action:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing parameters"})
            }

        # 查詢 DynamoDB 確認請求存在
        response = dynamodb.get_item(
            TableName="IAMRoleRequests",
            Key={"request_id": {"S": request_id}}
        )

        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Request not found"})
            }

        request_item = response["Item"]
        role_name = request_item["role_name"]["S"]
        policy_arns = request_item.get("policy_arns", {}).get("SS", [])
        current_status = request_item.get("status", {}).get("S", "")

        # === 拒絕 "reject" ===
        if action == "reject":
            dynamodb.update_item(
                TableName="IAMRoleRequests",
                Key={"request_id": {"S": request_id}},
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": {"S": "rejected"}}
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Request rejected"})
            }

        # === 批准 "approve" ===
        if action == "approve":
            if current_status == "approved":
                return {
                    "statusCode": 409,
                    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": "Request already approved"})
                }

            # 檢查 IAM Role 是否已存在
            try:
                iam.get_role(RoleName=role_name)
            except iam.exceptions.NoSuchEntityException:
                # Role 不存在，建立 Role
                assume_role_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }
                iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy)
                )

            # === 檢查並附加所有 Policies ===
            for policy_arn in policy_arns:
                try:
                    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                except Exception as e:
                    return {
                        "statusCode": 500,
                        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                        "body": json.dumps({"error": f"Failed to attach policy {policy_arn}", "details": str(e)})
                    }

            # === 更新 DynamoDB 狀態 ===
            dynamodb.update_item(
                TableName="IAMRoleRequests",
                Key={"request_id": {"S": request_id}},
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": {"S": "approved"}}
            )

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Role created and policies attached", "role": role_name, "policy_arns": policy_arns})
            }

        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Invalid action"})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
