param(
    [string]$ProjectId = "sphereless",
    [string]$Region = "us-central1",
    [string]$ServiceName = "items-service-v2",
    [string]$FirestoreCollection = "items_catalog_v2",
    [string]$VertexLocation = "global",
    [string]$VertexDataStoreId = "items-datastore-v2",
    [string]$AllowUnauthenticated = "true",
    [string]$BuildPythonVersion = "3.13"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting project..."
gcloud config set project $ProjectId | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set gcloud project: $ProjectId"
}

Write-Host "Deploying to Cloud Run from source..."
$authFlag = "--no-allow-unauthenticated"
if ($AllowUnauthenticated -eq "true") {
    $authFlag = "--allow-unauthenticated"
}

gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --project $ProjectId `
    --platform managed `
    $authFlag `
    --set-build-env-vars "GOOGLE_PYTHON_VERSION=$BuildPythonVersion,GOOGLE_ENTRYPOINT=uvicorn app.main:app --host 0.0.0.0 --port 8080" `
    --set-env-vars "APP_NAME=items-service,APP_ENV=prod,GCP_PROJECT_ID=$ProjectId,FIRESTORE_ITEMS_COLLECTION_SERVICE=$FirestoreCollection,VERTEX_SEARCH_LOCATION_SERVICE=$VertexLocation,VERTEX_SEARCH_ITEMS_DATASTORE_ID_SERVICE=$VertexDataStoreId"

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Run deployment failed for service $ServiceName"
}

Write-Host "Deployment finished."
Write-Host "Get URL with: gcloud run services describe $ServiceName --region $Region --project $ProjectId --format='value(status.url)'"
