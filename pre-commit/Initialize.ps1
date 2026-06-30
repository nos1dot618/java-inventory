[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Path
)

$ModuleDirectory = Split-Path $PSScriptRoot -Parent

Import-Module (Join-Path $ModuleDirectory "PSLogger.psm1") -Force
Import-Module (Join-Path $ModuleDirectory "Config.psm1") -Force

$GitDirectory = Join-Path $Path ".git"

if (-not (Test-Path $GitDirectory -PathType Container)) {
    Write-ErrorLog -Message "'$Path' is not a git repository (.git directory not found)." -Exit
}

$GitHooksDirectory = Join-Path $GitDirectory "hooks"

New-Item -ItemType Directory -Path $GitHooksDirectory -Force | Out-Null
Write-InfoLog -Message "Created directory '$GitHooksDirectory'."

$PreCommitHookSource = Join-Path $PSScriptRoot "pre-commit"
$PreCommitHookDestination = Join-Path $GitHooksDirectory "pre-commit"

try {
    New-Item `
        -ItemType SymbolicLink `
        -Path $PreCommitHookDestination `
        -Target $PreCommitHookSource `
        -Force `
        -ErrorAction Stop | Out-Null
    Write-InfoLog -Message "Created symlink '$PreCommitHookDestination' -> '$PreCommitHookSource'."
}
catch {
    Write-ErrorLog -Message "Symlink creation failed (admin privileges required). Falling back to copy."
    Copy-Item -Path $PreCommitHookSource -Destination $PreCommitHookDestination -Force
    Write-InfoLog -Message "Copied hook '$PreCommitHookDestination' -> '$PreCommitHookSource'."
}
