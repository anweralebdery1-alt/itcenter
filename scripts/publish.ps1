param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Message,

    [switch]$PrivateRepositoryConfirmed
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

if (-not $PrivateRepositoryConfirmed) {
    throw "Confirm that the GitHub repository is PRIVATE by adding -PrivateRepositoryConfirmed."
}

$branch = (git branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Publishing is allowed only from the main branch. Current branch: $branch"
}

Invoke-Checked git @("fetch", "origin", "main")

$behindAhead = (git rev-list --left-right --count "origin/main...HEAD") -split "\s+"
if ([int]$behindAhead[0] -gt 0) {
    throw "Local main is behind GitHub. Pull and review the remote changes first."
}

Invoke-Checked python @("manage.py", "check")
Invoke-Checked python @("manage.py", "makemigrations", "--check", "--dry-run")
Invoke-Checked python @("manage.py", "test")
Invoke-Checked git @("diff", "--check")
Invoke-Checked git @("add", "--all")

$stagedFiles = @(git diff --cached --name-only)
if ($stagedFiles.Count -eq 0) {
    Write-Host "No changes to publish."
    exit 0
}

$forbidden = @(
    $stagedFiles | Where-Object {
        (
            $_ -match '(^|/)\.env($|\.)' -and
            $_ -notmatch '(^|/)\.env\.production\.example$'
        ) -or
        $_ -match '(^|/)(db\.sqlite3$|store\.db$|store_data\.json$|media/|staticfiles/)' -or
        $_ -match '\.(pem|key|p12|pfx)$'
    }
)
if ($forbidden.Count -gt 0) {
    throw "Sensitive or generated files are staged: $($forbidden -join ', ')"
}

git grep --cached -q -I -E 'sk_live_[A-Za-z0-9]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
if ($LASTEXITCODE -eq 0) {
    throw "A possible live API key or private key was found in staged files."
}
if ($LASTEXITCODE -ne 1) {
    throw "Secret scan could not be completed."
}

Invoke-Checked git @("commit", "-m", $Message)
Invoke-Checked git @("push", "origin", "main")

Write-Host ""
Write-Host "Published to GitHub successfully."
Write-Host "Next, run on Contabo: sudo bash /var/www/itcenterstore/scripts/deploy_server.sh"
