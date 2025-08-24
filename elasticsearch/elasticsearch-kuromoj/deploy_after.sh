RESOURCE_GROUP="poc-search-suggest"
APP_NAME="elasticsearch"

# ボリュームマウントを更新
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --volume-name esdata \
  --volume-storage-name esdata \
  --volume-storage-type AzureFile \
  --mount-path /usr/share/elasticsearch/data