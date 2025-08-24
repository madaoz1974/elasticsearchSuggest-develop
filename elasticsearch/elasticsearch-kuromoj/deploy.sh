# 環境変数の設定
RESOURCE_GROUP="poc-search-suggest"
ENVIRONMENT="poc-search-suggest-env"
APP_NAME="elasticsearch"
IMAGE="crmsprpocjpe01.azurecr.io/elasticsearch-kuromoji:7.10.0"
ACR_NAME="crmsprpocjpe01"

# ACRのパスワードを取得（もしくは手動で設定）
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

STORAGE_ACCOUNT="pocsearchsuggest"
STORAGE_KEY=$(az storage account keys list \  
  --resource-group $RESOURCE_GROUP \  
  --account-name $STORAGE_ACCOUNT \  
  --query '[0].value' -o tsv)

# Elasticsearchアプリを作成（ボリューム指定を修正）
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT \
  --image $IMAGE \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --secrets storagekey=$STORAGE_KEY \
  --target-port 9200 \
  --ingress external \
  --cpu 1 \
  --memory 2.0Gi \
  --min-replicas 0 \
  --max-replicas 10 \
  --env-vars "discovery.type=single-node" "xpack.security.enabled=false" "ES_JAVA_OPTS=-Xms512m -Xmx512m"