. .\Commons.ps1

function CompileCheckstyleCheck
{
    param (
        [Parameter(Mandatory)]
        [string]$ClassName
    )
    javac `
        -cp ".\resources\checkstyle-12.3.0-all.jar" `
        -d ".\$BuildDirectory\" `
        ".\src\main\java\fun\ninth\$ClassName.java"
    if ($LASTEXITCODE -eq 0)
    {
        Info -Message "Generated class-file '.\$BuildDirectory\fun\ninth\$ClassName.class'."
    }
    else
    {
        Error -Message "Failed to generate class-file '.\$BuildDirectory\fun\ninth\$ClassName.class'."
    }
}

New-Item -ItemType Directory -Path ".\$BuildDirectory\" -Force > $null
Info -Message "Created directory '.\$BuildDirectory\'."

@(
    "MethodInventoryCheck"
    "RestApiInventoryCheck"
) | ForEach-Object {
    CompileCheckstyleCheck -ClassName $_
}

jar `
  cf ".\$BuildDirectory\$ChecksJarFileName.jar" `
  -C "$BuildDirectory" "fun\ninth\" `
  -C ".\resources" "checkstyle_packages.xml"
if ($LASTEXITCODE -eq 0)
{
    Info -Message "Generated jar '.\$BuildDirectory\$ChecksJarFileName.jar'."
}
else
{
    Info -Message "Failed to generated jar '.\$BuildDirectory\$ChecksJarFileName.jar'."
}
