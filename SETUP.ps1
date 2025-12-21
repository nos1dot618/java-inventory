$BuildDirectory = "build"

New-Item -ItemType Directory -Path ".\build\" -Force > $null
Write-Host "[INFO] Created directory '.\$BuildDirectory\'."

javac `
  -cp ".\resources\checkstyle-12.3.0-all.jar" `
  -d ".\$BuildDirectory\" `
  ".\src\main\java\fun\ninth\MethodInventoryCheck.java"
Write-Host "[INFO] Generated class-file '.\$BuildDirectory\fun\ninth\MethodInventoryCheck.class'."

jar `
  cf ".\$BuildDirectory\MethodInventoryCheck.jar" `
  -C "$BuildDirectory" "fun\ninth\" `
  -C ".\resources" "checkstyle_packages.xml"
Write-Host "[INFO] Generated jar '.\$BuildDirectory\MethodInventoryCheck.jar'."