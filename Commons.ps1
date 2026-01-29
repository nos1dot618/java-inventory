$BuildDirectory = "build"
$ChecksJarFileName = "CheckstyleChecks"

function Log
{
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

function Error
{
    param (
        [Parameter(Mandatory)]
        [string]$Message,
        [switch]$Exit
    )
    Log -Level "ERROR" -Color Red -Message $Message
    if ($Exit)
    {
        exit 1
    }
}

function Info
{
    param (
        [Parameter(Mandatory)]
        [string]$Message
    )
    Log -Level "INFO" -Color Blue -Message $Message
}
