param(
    [string]$ProjectId = "sphereless",
    [string]$Location = "global",
    [string]$DatastoreId = "items-datastore-v3",
    [string]$Collection = "items_catalog_v2",
    [int]$Limit = 1000,
    [switch]$Prune,
    [switch]$IncludeContent,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$argsList = @(
    ".\\scripts\\sync_items_to_vertex.py",
    "--project-id", $ProjectId,
    "--location", $Location,
    "--datastore-id", $DatastoreId,
    "--collection", $Collection,
    "--limit", "$Limit"
)

if ($Prune) {
    $argsList += "--prune"
}
if ($IncludeContent) {
    $argsList += "--include-content"
}
if ($DryRun) {
    $argsList += "--dry-run"
}

.\.venv\Scripts\python.exe @argsList
