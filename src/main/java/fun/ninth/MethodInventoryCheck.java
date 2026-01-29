package fun.ninth;

import java.util.Objects;

import com.puppycrawl.tools.checkstyle.api.AbstractCheck;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

public class MethodInventoryCheck extends AbstractCheck {

    private String currentPackage;
    private String currentClass;

    @Override
    public void visitToken(DetailAST detailAST) {
        switch (detailAST.getType()) {
            case TokenTypes.PACKAGE_DEF: {
                DetailAST dotOrIdentifierAST = detailAST.findFirstToken(TokenTypes.DOT);
                if (dotOrIdentifierAST != null) {
                    currentPackage = getFullIdentifier(dotOrIdentifierAST);
                } else {
                    currentPackage = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.IDENT)).getText();
                }
                break;
            }
            case TokenTypes.CLASS_DEF: {
                currentClass = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.IDENT)).getText();
                break;
            }
            case TokenTypes.METHOD_DEF: {
                String method = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.IDENT)).getText();
                System.out.printf("[DEBUG] [Method Inventory Check] %s %s %s%n", currentClass, currentPackage, method);
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

    @Override
    public int[] getDefaultTokens() {
        return new int[]{TokenTypes.PACKAGE_DEF, TokenTypes.CLASS_DEF, TokenTypes.METHOD_DEF};
    }

    private String getFullIdentifier(DetailAST detailAST) {
        return switch (detailAST.getType()) {
            case TokenTypes.IDENT -> detailAST.getText();
            case TokenTypes.DOT ->
                    String.format("%s.%s", getFullIdentifier(detailAST.getFirstChild()), getFullIdentifier(detailAST.getLastChild()));
            default -> "";
        };
    }

}