import json
import boto3

iam = boto3.client("iam")

def lambda_handler(event, context):
    try:
        policies = []
        marker = None

        while True:
            if marker:
                response = iam.list_policies(Scope="AWS", Marker=marker)
            else:
                response = iam.list_policies(Scope="AWS")

            policies.extend(
                [{"name": p["PolicyName"], "arn": p["Arn"]} for p in response["Policies"]]
            )

            if "Marker" in response:
                marker = response["Marker"]
            else:
                break

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps(policies)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
