import time
import datetime
import boto3
import json
import uuid

dynamodb = boto3.client("dynamodb")
sns = boto3.client("sns")

SNS_TOPIC_ARN = "arn:aws:sns:us-west-1:027060312592:Brian-IAMRoleApproval"
API_GATEWAY_BASE_URL = "https://rk1obuoifa.execute-api.us-west-1.amazonaws.com/prod"
DEFAULT_TTL_DAYS = 7

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        body = event.get("body", "{}")
        request_body = json.loads(body) if body else {}

        request_id = str(uuid.uuid4())
        role_name = request_body.get("role_name")
        policy_arns = request_body.get("policy_arns", [])
        requester = request_body.get("requester")
        duration_hours = request_body.get("duration_hours")
        expiration_time_input = request_body.get("expiration_time")

        if not role_name or not policy_arns or not requester:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing parameters"})
            }

        current_time = int(time.time())
        if expiration_time_input:
            expiration_time = int(expiration_time_input)
        elif duration_hours:
            expiration_time = current_time + (int(duration_hours) * 3600)
        else:
            expiration_time = current_time + (DEFAULT_TTL_DAYS * 86400)

        dynamodb.put_item(
            TableName="IAMRoleRequests",
            Item={
                "request_id": {"S": request_id},
                "role_name": {"S": role_name},
                "policy_arns": {"SS": policy_arns},
                "status": {"S": "pending"},
                "requester": {"S": requester},
                "timestamp": {"S": datetime.datetime.utcnow().replace(microsecond=0).isoformat()},
                "expiration_time": {"N": str(expiration_time)}
            }
        )

        sns_message = (
            f"New IAM Role request:\n"
            f"Role: {role_name}\n"
            f"Policies: {', '.join(policy_arns)}\n"
            f"Requester: {requester}\n\n"
            f"Approve request:\n{API_GATEWAY_BASE_URL}/approve-iam-role?request_id={request_id}&action=approve\n\n"
            f"Reject request:\n{API_GATEWAY_BASE_URL}/reject-iam-role?request_id={request_id}&action=reject\n\n"
            # f"Delete request:\n{API_GATEWAY_BASE_URL}/reject-iam-role?request_id={request_id}&action=delete\n\n"
            f"Request expires at: {datetime.datetime.utcfromtimestamp(expiration_time).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="IAM Role Approval Needed",
            Message=sns_message
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Request submitted",
                "request_id": request_id,
                "expiration_time": expiration_time
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
