package fun.ninth.inventory.checkstyle;

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
                DetailAST modifiers = detailAST.findFirstToken(TokenTypes.MODIFIERS);
                String accessModifier = getAccessModifier(modifiers);
                System.out.printf("%s,%s,%s,%s%n", currentPackage, currentClass, method, accessModifier);
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
        return new int[] { TokenTypes.PACKAGE_DEF, TokenTypes.CLASS_DEF, TokenTypes.METHOD_DEF };
    }

    private String getAccessModifier(DetailAST modifiers) {
        if (modifiers == null) {
            return "package-private";
        }
        if (modifiers.findFirstToken(TokenTypes.LITERAL_PUBLIC) != null) {
            return "public";
        }
        if (modifiers.findFirstToken(TokenTypes.LITERAL_PROTECTED) != null) {
            return "protected";
        }
        if (modifiers.findFirstToken(TokenTypes.LITERAL_PRIVATE) != null) {
            return "private";
        }
        return "package-private";
    }

    private String getFullIdentifier(DetailAST detailAST) {
        return switch (detailAST.getType()) {
            case TokenTypes.IDENT -> detailAST.getText();
            case TokenTypes.DOT -> String.format("%s.%s", getFullIdentifier(detailAST.getFirstChild()),
                    getFullIdentifier(detailAST.getLastChild()));
            default -> "";
        };
    }

}
