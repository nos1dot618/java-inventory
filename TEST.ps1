$BuildDirectory = "build"

java -cp "resources/checkstyle-12.3.0-all.jar;$BuildDirectory/MethodInventoryCheck.jar" `
  com.puppycrawl.tools.checkstyle.Main `
  -c ".\resources\method_inventory_check_config.xml" `
  .\dev-test\src\
