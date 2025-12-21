package fun.ninth;

import com.puppycrawl.tools.checkstyle.api.AbstractCheck;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

public class MethodInventoryCheck extends AbstractCheck {

    private String currentPackage;
    private String currentClass;

    private String getFullIdentifier(DetailAST detailAST) {
        return switch (detailAST.getType()) {
            case TokenTypes.IDENT -> detailAST.getText();
            case TokenTypes.DOT ->
                    String.format("%s.%s", getFullIdentifier(detailAST.getFirstChild()), getFullIdentifier(detailAST.getLastChild()));
            default -> "";
        };
    }


    @Override
    public int[] getDefaultTokens() {
        return new int[]{TokenTypes.PACKAGE_DEF, TokenTypes.CLASS_DEF, TokenTypes.METHOD_DEF};
    }

    @Override
    public void visitToken(DetailAST detailAST) {
        switch (detailAST.getType()) {
            case TokenTypes.PACKAGE_DEF: {
                DetailAST dotOrIdentifierAST = detailAST.findFirstToken(TokenTypes.DOT);
                if (dotOrIdentifierAST != null) {
                    currentPackage = getFullIdentifier(dotOrIdentifierAST);
                } else {
                    DetailAST ident = detailAST.findFirstToken(TokenTypes.IDENT);
                    currentPackage = ident.getText();
                }
                break;
            }
            case TokenTypes.CLASS_DEF: {
                currentClass = detailAST.findFirstToken(TokenTypes.IDENT).getText();
                break;
            }
            case TokenTypes.METHOD_DEF: {
                String method = detailAST.findFirstToken(TokenTypes.IDENT).getText();
                System.out.println(String.format("[DEBUG] [Method Inventory Check] %s %s %s", currentClass, currentPackage, method));
                break;
            }
        }
    }

    @Override
    public int[] getRequiredTokens() {
        return getDefaultTokens();
    }

    @Override
    public int[] getAcceptableTokens() {
        return getDefaultTokens();
    }

}