param(
    [string]$ProjectId = "sphereless",
    [string]$Region = "us-central1",
    [string]$FirestoreLocation = "nam5",
    [string]$VertexLocation = "global",
    [string]$VertexDataStoreId = "items-datastore-v2",
    [string]$VertexDisplayName = "Items Datastore V2",
    [string]$VertexContentConfig = "CONTENT_REQUIRED",
    [string]$ArtifactRepo = "items-service-repo"
)

$ErrorActionPreference = "Stop"

function Invoke-GCloud {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [switch]$CaptureOutput
    )

    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $argString = ($Args | ForEach-Object {
            if ($_ -match "\s") {
                '"' + ($_ -replace '"', '\\"') + '"'
            } else {
                $_
            }
        }) -join " "

        $process = Start-Process -FilePath "gcloud.cmd" -ArgumentList $argString -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
        $stdout = Get-Content $stdoutFile -Raw
        $stderr = Get-Content $stderrFile -Raw

        if ($process.ExitCode -ne 0) {
            throw "gcloud failed: gcloud $($Args -join ' ')`n$stderr$stdout"
        }

        if ($CaptureOutput) {
            return $stdout
        }

        if ($stdout) {
            Write-Host $stdout -NoNewline
        }
    } finally {
        Remove-Item $stdoutFile -ErrorAction SilentlyContinue
        Remove-Item $stderrFile -ErrorAction SilentlyContinue
    }
}

function Get-VertexDataStoreBaseCommand {
    $candidates = @(
        @("discovery-engine", "data-stores"),
        @("beta", "discovery-engine", "data-stores"),
        @("alpha", "discovery-engine", "data-stores")
    )

    foreach ($candidate in $candidates) {
        try {
            Invoke-GCloud -Args @($candidate + @("list", "--help")) | Out-Null
            return $candidate
        } catch {
            continue
        }
    }

    return $null
}

function Ensure-VertexDataStoreViaRest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectId,
        [Parameter(Mandatory = $true)]
        [string]$Location,
        [Parameter(Mandatory = $true)]
        [string]$DataStoreId,
        [Parameter(Mandatory = $true)]
        [string]$DisplayName,
        [Parameter(Mandatory = $true)]
        [string]$ContentConfig
    )

    $token = (Invoke-GCloud -CaptureOutput -Args @("auth", "application-default", "print-access-token")).Trim()
    if (-not $token) {
        throw "Failed to get access token from gcloud auth application-default print-access-token"
    }

    $headers = @{
        Authorization = "Bearer $token"
        "x-goog-user-project" = $ProjectId
    }
    $baseUrl = "https://discoveryengine.googleapis.com/v1/projects/$ProjectId/locations/$Location/collections/default_collection/dataStores"

    $listResponse = Invoke-RestMethod -Method GET -Uri $baseUrl -Headers $headers -ErrorAction Stop
    $existing = @($listResponse.dataStores) | Where-Object {
        $_.name -match "/$([regex]::Escape($DataStoreId))$"
    }

    if ($existing) {
        Write-Host "Vertex AI Search datastore already exists: $DataStoreId"
        return
    }

    $createUrl = "${baseUrl}?dataStoreId=$DataStoreId"
    $body = @{
        displayName = $DisplayName
        industryVertical = "GENERIC"
        solutionTypes = @("SOLUTION_TYPE_SEARCH")
        contentConfig = $ContentConfig
    } | ConvertTo-Json -Depth 5

    $operation = Invoke-RestMethod -Method POST -Uri $createUrl -Headers ($headers + @{ "Content-Type" = "application/json" }) -Body $body -ErrorAction Stop

    $opName = $operation.name
    if (-not $opName) {
        throw "Datastore creation did not return an operation name"
    }

    $opUrl = "https://discoveryengine.googleapis.com/v1/$opName"
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        $opStatus = Invoke-RestMethod -Method GET -Uri $opUrl -Headers $headers -ErrorAction Stop
        if ($opStatus.done -eq $true) {
            if ($opStatus.error) {
                throw "Datastore creation failed: $($opStatus.error.message)"
            }
            Write-Host "Created Vertex AI Search datastore: $DataStoreId"
            return
        }
    }

    throw "Timed out waiting for datastore creation operation: $opName"
}

Write-Host "[1/6] Setting gcloud project..."
Invoke-GCloud -Args @("config", "set", "project", $ProjectId) | Out-Null

Write-Host "[2/6] Enabling required services..."
Invoke-GCloud -Args @(
    "services", "enable",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "discoveryengine.googleapis.com",
    "--project", $ProjectId
)

Write-Host "[3/6] Creating Artifact Registry repo if missing..."
$repoNames = Invoke-GCloud -CaptureOutput -Args @(
    "artifacts", "repositories", "list",
    "--project", $ProjectId,
    "--location", $Region,
    "--format=value(name)"
)
$repoEntries = ($repoNames -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
$repoExists = ($repoEntries -contains $ArtifactRepo) -or ($repoEntries -match "/$([regex]::Escape($ArtifactRepo))$")
if (-not $repoExists) {
    Invoke-GCloud -Args @(
        "artifacts", "repositories", "create", $ArtifactRepo,
        "--repository-format=docker",
        "--location=$Region",
        "--description=Docker repo for items service",
        "--project", $ProjectId
    )
    Write-Host "Created Artifact Registry repo: $ArtifactRepo"
} else {
    Write-Host "Artifact Registry repo already exists: $ArtifactRepo"
}

Write-Host "[4/6] Creating Firestore database if missing..."
$fsDb = Invoke-GCloud -CaptureOutput -Args @("firestore", "databases", "list", "--project", $ProjectId, "--format=value(name)")
if (-not $fsDb) {
    Invoke-GCloud -Args @(
        "firestore", "databases", "create",
        "--location=$FirestoreLocation",
        "--type=firestore-native",
        "--project", $ProjectId
    )
    Write-Host "Created Firestore database in $FirestoreLocation"
} else {
    Write-Host "Firestore database already exists"
}

Write-Host "[5/6] Ensuring Discovery Engine components are available..."
try {
    Invoke-GCloud -Args @("components", "install", "alpha", "--quiet") | Out-Null
} catch {
    Write-Host "gcloud alpha component may already be available or managed externally. Continuing..."
}

Write-Host "[6/6] Creating Vertex AI Search datastore if missing..."
$vertexBase = Get-VertexDataStoreBaseCommand
if ($null -eq $vertexBase) {
    Write-Warning "No supported gcloud Discovery Engine command group found on this machine."
    Write-Host "Using REST API fallback for Vertex AI Search datastore creation..."
    Ensure-VertexDataStoreViaRest `
        -ProjectId $ProjectId `
        -Location $VertexLocation `
        -DataStoreId $VertexDataStoreId `
        -DisplayName $VertexDisplayName `
        -ContentConfig $VertexContentConfig
} else {
    $listArgs = @($vertexBase + @(
        "list",
        "--location=$VertexLocation",
        "--collection=default_collection",
        "--project", $ProjectId,
        "--format=value(name)"
    ))
    $existing = Invoke-GCloud -CaptureOutput -Args $listArgs
    $existingEntries = ($existing -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })

    if (-not (($existingEntries -contains $VertexDataStoreId) -or ($existingEntries -match "/$([regex]::Escape($VertexDataStoreId))$"))) {
        $createArgs = @($vertexBase + @(
            "create",
            "--location=$VertexLocation",
            "--collection=default_collection",
            "--data-store-id=$VertexDataStoreId",
            "--display-name=$VertexDisplayName",
            "--industry-vertical=GENERIC",
            "--solution-types=SOLUTION_TYPE_SEARCH",
            "--content-config=$VertexContentConfig",
            "--project", $ProjectId
        ))
        Invoke-GCloud -Args $createArgs
        Write-Host "Created Vertex AI Search datastore: $VertexDataStoreId"
    } else {
        Write-Host "Vertex AI Search datastore already exists: $VertexDataStoreId"
    }
}

Write-Host "Done. Resources are ready (or already existed)."
