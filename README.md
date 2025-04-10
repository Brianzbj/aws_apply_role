# IAM Role Request API Setup

本指南提供使用 API Gateway、Lambda 和 DynamoDB 設置 AWS IAM Role Request API 的步驟。

## 目錄
- [前置條件](#%E5%89%8D%E7%BD%AE%E6%A2%9D%E4%BB%B6)
- [DynamoDB 設置](#dynamodb-%E8%A8%AD%E7%BD%AE)
  - [建立資料表](#1-%E5%BB%BA%E7%AB%8B-dynamodb-%E8%B3%87%E6%96%99%E8%A1%A8)
  - [啟用 TTL](#2-%E5%95%9F%E7%94%A8-dynamodb-ttl)
  - [配置 Streams](#3-%E9%85%8D%E7%BD%AE-dynamodb-streams)
- [API Gateway 設置](#api-gateway-%E8%A8%AD%E7%BD%AE)
  - [建立 API](#1-%E5%BB%BA%E7%AB%8B-api-gateway)
  - [Lambda 整合](#2-%E5%BB%BA%E7%AB%8B-lambda-%E6%95%B4%E5%90%88)
  - [建立路由](#3-%E5%BB%BA%E7%AB%8B-api-%E8%B7%AF%E7%94%B1)
  - [啟用 CORS](#5-%E5%95%9F%E7%94%A8-cors)
  - [部署 API](#6-%E9%83%A8%E7%BD%B2-api)
- [API 測試](#%E6%B8%AC%E8%A9%A6-api)
- [列出 AWS Policies API](#%E5%88%97%E5%87%BA-aws-policies-api)
- [未來增強](#%E6%9C%AA%E4%BE%86%E5%A2%9E%E5%BC%B7)

## 前置條件
- 已安裝並配置 AWS CLI
- 擁有 AWS 帳戶，具備創建 DynamoDB、API Gateway、Lambda 和 IAM Policies 的權限

## DynamoDB 設置

### 1. 建立 DynamoDB 資料表
```sh
aws dynamodb create-table \
    --table-name IAMRoleRequests \
    --attribute-definitions AttributeName=request_id,AttributeType=S \
    --key-schema AttributeName=request_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-west-1
```

### 2. 啟用 DynamoDB TTL
```sh
aws dynamodb update-time-to-live \
    --table-name IAMRoleRequests \
    --time-to-live-specification "Enabled=true, AttributeName=expiration_time"
```

### 3. 配置 DynamoDB Streams
```sh
aws dynamodb update-table \
    --table-name IAMRoleRequests \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

## API Gateway 設置

### 1. 建立 API Gateway
```sh
aws apigatewayv2 create-api \
    --name IAMRoleAPI \
    --protocol-type HTTP
```

### 2. 建立 Lambda 整合
```sh
aws apigatewayv2 create-integration \
    --api-id ${api-id} \
    --integration-type AWS_PROXY \
    --integration-uri "${lambda_arn}" \
    --payload-format-version "2.0"
```

### 3. 建立 API 路由
```sh
aws apigatewayv2 create-route \
    --api-id ${api-id} \
    --route-key "POST /request-iam-role" \
    --target "integrations/${integration-id}"
```

### 4. 更新路由綁定（可選）
```sh
aws apigatewayv2 update-route \
    --api-id ${api-id} \
    --route-id ${RouteId} \
    --target "integrations/${integration-id}"
```

### 5. 啟用 CORS
```sh
aws apigatewayv2 update-api \
    --api-id ${api-id} \
    --cors-configuration AllowOrigins='["*"]' \
    --cors-configuration AllowMethods='["POST", "OPTIONS"]' \
    --cors-configuration AllowHeaders='["Content-Type"]'
```

### 6. 部署 API
```sh
aws apigatewayv2 create-deployment --api-id ${api-id}
```

## 測試 API

### 獲取 API Gateway URL
```sh
aws apigatewayv2 get-api --api-id ${api-id}
```

### 測試 API
```sh
curl -X POST "https://rk1obuoifa.execute-api.us-west-1.amazonaws.com/prod/request-iam-role" \
-H "Content-Type: application/json" \
-d '{"role_name": "TestRole", "policy_arn": "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess", "requester": "User"}'
```

## 列出 AWS Policies API

### 1. 建立 API Gateway
```sh
aws apigateway create-rest-api \
    --name "IAMPoliciesAPI" \
    --region us-west-1 \
    --protocol-type REST \
    --endpoint-configuration types=REGIONAL
```

### 2. 獲取 Root Resource ID
```sh
aws apigateway get-resources --rest-api-id abcdefghij
```

### 3. 建立 `/list-policies` 路由
```sh
aws apigateway create-resource \
    --rest-api-id abcdefghij \
    --parent-id xyz123 \
    --path-part list-policies
```

### 4. 配置 GET 方法
```sh
aws apigateway put-method \
    --rest-api-id abcdefghij \
    --resource-id list456 \
    --http-method GET \
    --authorization-type "NONE"
```

### 5. 部署 API
```sh
aws apigateway create-deployment \
    --rest-api-id abcdefghij \
    --stage-name prod
```

### 6. 授權 API Gateway 調用 Lambda
```sh
aws lambda add-permission \
    --function-name list-policy \
    --statement-id apigateway-access \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-west-1:027060312592:abcdefghij/*/GET/list-policies"
```

## 未來增強
- **OAuth2 Proxy & SSO 整合**（可選）- 使用單一登入（SSO）保護 API。