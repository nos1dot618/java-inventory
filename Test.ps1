[CmdletBinding()]
param (
    [switch]$MethodInventory,
    [switch]$RestApiInventory
)

. .\Commons.ps1

$ClassPath = "resources/checkstyle-12.3.0-all.jar;$BuildDirectory/$ChecksJarFileName.jar"

if ($MethodInventory -and $RestApiInventory)
{
    Error -Message "Please specify only one of -MethodInventory or -RestApiInventory." -Exit
}
elseif ($MethodInventory)
{
    $Config = ".\resources\configs\method_inventory_check_config.xml"
    Info -Message "Running method-inventory-checkstyle."
}
elseif ($RestApiInventory)
{
    $Config = ".\resources\configs\rest_api_inventory_check_config.xml"
    Info -Message "Running REST-API-inventory-checkstyle."
}
else
{
    Error -Message  "No check type specified. Use -MethodInventory or -RestApiInventory." -Exit
}

java -cp $ClassPath `
    com.puppycrawl.tools.checkstyle.Main `
    -c $Config `
    .\dev-test\src\
