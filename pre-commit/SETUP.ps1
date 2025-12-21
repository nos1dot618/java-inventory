if (-not (Test-Path ".git" -PathType Container)) {
    throw "ERROR: Not a git repository (.git directory not found)."
}

$GitHooksDirectory = Join-Path ".git" "hooks"
New-Item -ItemType Directory -Path $GitHooksDirectory -Force | Out-Null

# Append $CheckstyleIgnoreEntry to .gitignore
$GitIgnorePath = ".gitignore"
$CheckstyleIgnoreEntry = ".checkstyle/"
if (-not (Test-Path $GitIgnorePath)) {
    New-Item -ItemType File -Path $GitIgnorePath | Out-Null
}
$existingGitignoreContent = Get-Content $GitIgnorePath -ErrorAction SilentlyContinue
# Append only if not already present
if ($existingGitignoreContent -notcontains $CheckstyleIgnoreEntry) {
    Add-Content -Path $GitIgnorePath -Value $CheckstyleIgnoreEntry
}

# Create temp-directory
$TempDirectory = New-Item -ItemType Directory -Path (
    Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid())
)

try {
    # Shallow-Clone repository
    git clone --depth 1 https://github.com/nos1dot618/git-hook-java.git $TempDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "ERROR: git clone failed."
    }

    # Move .checkstyle (replace if exists)
    $CheckstyleDestinationDirectory = ".\.checkstyle"
    if (Test-Path $CheckstyleDestinationDirectory) {
        Remove-Item $CheckstyleDestinationDirectory -Recurse -Force
    }
    Move-Item (Join-Path $TempDirectory ".checkstyle") $CheckstyleDestinationDirectory

    # Move pre-commit hook
    $PreCommitHookSource = Join-Path $TempDirectory "pre-commit"
    $PreCommitHookDestination = Join-Path $GitHooksDirectory "pre-commit"

    Move-Item $PreCommitHookSource $PreCommitHookDestination -Force
}
finally {
    # Always cleanup temp-directory
    if (Test-Path $TempDirectory) {
        Remove-Item $TempDirectory -Recurse -Force
    }
}
