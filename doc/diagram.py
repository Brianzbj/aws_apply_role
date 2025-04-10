from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.network import APIGateway, Route53, CloudFront
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SNS
from diagrams.aws.security import IAMRole
from diagrams.aws.general import User as Admin
from diagrams.onprem.client import User
from diagrams.aws.storage import S3
from diagrams.aws.database import DynamodbStreams

with Diagram("IAM Role Request Flow", show=False, direction="TB"):

    # **使用者從 Route 53 進入**
    route53 = Route53("Route 53\n(request-rule.train.nextlink.technology)")
    cloudfront = CloudFront("CloudFront\n(d1p9exveeebyt.cloudfront.net)")
    s3 = S3("S3 Bucket\n(存放 index.html)")

    user = User("User")
    user >> Edge(label="存取網域") >> route53
    route53 >> Edge(label="A Alias 到 CloudFront") >> cloudfront
    cloudfront >> Edge(label="提供靜態網站") >> s3
    
    # **前端 (S3) 透過 API Gateway 取得 IAM Policies**
    with Cluster(""):
        api_gateway_policies = APIGateway("API Gateway (List Policies)")
        lambda_list_policies = Lambda("Lambda_List_Policies\n(取得 IAM Policies)")

        s3 >> Edge(label="GET /list-policies") >> api_gateway_policies
        api_gateway_policies >> Edge(label="呼叫 Lambda") >> lambda_list_policies
        lambda_list_policies >> Edge(label="回傳 IAM Policies") >> s3
    
    # **使用者申請 IAM Role**
    with Cluster("User Request Flow"):
        api_gateway_user = APIGateway("API Gateway (User)")
        lambda_request_handler = Lambda("Lambda_Request_Handler\n(處理申請 & IAM Role)")
        dynamo_db = Dynamodb("DynamoDB\n(存申請記錄)\n[含TTL]")
        sns = SNS("SNS\n(通知管理員)")
        
        s3 >> Edge(label="POST /request") >> api_gateway_user
        api_gateway_user >> Edge(label="傳送請求") >> lambda_request_handler
        lambda_request_handler >> Edge(label="儲存請求") >> dynamo_db
        lambda_request_handler >> Edge(label="發送通知") >> sns
    
    # **管理員審批流程**
    with Cluster("Admin Approval Flow"):
        admin = Admin("Admin")
        api_gateway_admin = APIGateway("API Gateway (Admin)")
        lambda_request_confirm = Lambda("Lambda_Request_confirm\n(批准 / 拒絕 / 刪除 IAM Role)")
        
        sns >> Edge(label="Email / SMS 通知") >> admin
        admin >> Edge(label="批准 / 拒絕") >> api_gateway_admin
        api_gateway_admin >> Edge(label="更新請求狀態") >> lambda_request_confirm
        lambda_request_confirm >> Edge(label="更新 DynamoDB") >> dynamo_db
        lambda_request_confirm >> Edge(label="建立 IAM Role (如批准)") >> IAMRole("IAM Role")

    # **DynamoDB 過期處理**
    with Cluster("IAM Role Cleanup"):
        dynamodb_streams = DynamodbStreams("DynamoDB Streams\n(監聽刪除事件)")
        lambda_delete_role = Lambda("Lambda_DeleteRole\n(刪除過期 IAM Role)")

        dynamo_db >> Edge(label="TTL 過期，刪除記錄") >> dynamodb_streams  
        dynamodb_streams >> Edge(label="觸發 Lambda") >> lambda_delete_role 
        lambda_delete_role >> Edge(label="刪除 IAM Role") >> IAMRole("IAM Role (刪除)")
