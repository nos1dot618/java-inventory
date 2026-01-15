param (
    [Parameter(Mandatory)]
    [string]$SetupPath
)

function Log {
    param (
        [Parameter(Mandatory)]
        [string]$Level,
        [Parameter(Mandatory)]
        [ConsoleColor]$Color,
        [Parameter(Mandatory)]
        [string]$Message
    )
    Write-Host "[" -NoNewline
    Write-Host "$Level" -ForegroundColor $Color -NoNewline
    Write-Host "] $Message"
}

function Error {
    param (
        [Parameter(Mandatory)]
        [string]$Message,
        [switch]$Exit
    )
    Log -Level "ERROR" -Color Red -Message $Message
    if ($Exit) {
        exit 1
    }
}

function Info {
    param (
        [Parameter(Mandatory)]
        [string]$Message
    )
    Log -Level "INFO" -Color Blue -Message $Message
}

$GitDirectory = Join-Path $SetupPath ".git"
if (-not (Test-Path $GitDirectory -PathType Container)) {
    Error -Message "'$SetupPath' is not a git repository (.git directory not found)." -Exit
}

$GitHooksDirectory = Join-Path $GitDirectory "hooks"
New-Item -ItemType Directory -Path $GitHooksDirectory -Force | Out-Null
Info -Message "Created directory '$GitHooksDirectory'."

$PreCommitHookSource = Join-Path $PSScriptRoot "pre-commit"
$PreCommitHookDestination = Join-Path $GitHooksDirectory "pre-commit"
try {
    New-Item -ItemType SymbolicLink -Path $PreCommitHookDestination -Target $PreCommitHookSource `
        -Force -ErrorAction Stop | Out-Null
    Info -Message "Created symlink '$PreCommitHookDestination' -> '$PreCommitHookSource'."
}
catch {
    Error -Message "Symlink creation failed (admin-privileges required). Falling back to copy."
    Copy-Item $PreCommitHookSource -Destination $PreCommitHookDestination -Force
    Info -Message "Copied hook '$PreCommitHookDestination' -> '$PreCommitHookSource'."
}