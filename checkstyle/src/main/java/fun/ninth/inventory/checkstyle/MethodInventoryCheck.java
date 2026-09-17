package fun.ninth.inventory.checkstyle;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Objects;

import com.puppycrawl.tools.checkstyle.api.AbstractCheck;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

public class MethodInventoryCheck extends AbstractCheck {

    private String currentPackage;
    private final Deque<TypeContext> typeStack = new ArrayDeque<>();

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
            case TokenTypes.CLASS_DEF:
            case TokenTypes.INTERFACE_DEF:
            case TokenTypes.ENUM_DEF:
            case TokenTypes.RECORD_DEF:
            case TokenTypes.ANNOTATION_DEF: {
                String name = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.IDENT)).getText();
                String qualifiedName = buildQualifiedName(name);
                typeStack.push(new TypeContext(qualifiedName, detailAST.getType()));
                break;
            }
            case TokenTypes.METHOD_DEF: {
                if (typeStack.isEmpty()) {
                    // Method outside any type (shouldn't normally happen for valid Java)
                    break;
                }
                TypeContext enclosingType = typeStack.peek();
                String method = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.IDENT)).getText();
                DetailAST modifiers = detailAST.findFirstToken(TokenTypes.MODIFIERS);
                String accessModifier = getAccessModifier(modifiers, enclosingType, detailAST);
                System.out.printf("%s,%s,%s,%s%n", currentPackage, enclosingType.qualifiedName, method,
                        accessModifier);
                break;
            }
            default:
                break;
        }
    }

    @Override
    public void leaveToken(DetailAST detailAST) {
        switch (detailAST.getType()) {
            case TokenTypes.CLASS_DEF:
            case TokenTypes.INTERFACE_DEF:
            case TokenTypes.ENUM_DEF:
            case TokenTypes.RECORD_DEF:
            case TokenTypes.ANNOTATION_DEF: {
                typeStack.pop();
                break;
            }
            default:
                break;
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
        return new int[] {
                TokenTypes.PACKAGE_DEF,
                TokenTypes.CLASS_DEF,
                TokenTypes.INTERFACE_DEF,
                TokenTypes.ENUM_DEF,
                TokenTypes.RECORD_DEF,
                TokenTypes.ANNOTATION_DEF,
                TokenTypes.METHOD_DEF
        };
    }

    private String buildQualifiedName(String simpleName) {
        if (typeStack.isEmpty()) {
            return simpleName;
        }
        return typeStack.peek().qualifiedName + "." + simpleName;
    }

    /**
     * Determines the effective access modifier of a method, accounting for
     * implicit-public members of interfaces and annotation types.
     */
    private String getAccessModifier(DetailAST modifiers, TypeContext enclosingType, DetailAST methodDef) {
        if (modifiers != null) {
            if (modifiers.findFirstToken(TokenTypes.LITERAL_PUBLIC) != null) {
                return "public";
            }
            if (modifiers.findFirstToken(TokenTypes.LITERAL_PROTECTED) != null) {
                return "protected";
            }
            if (modifiers.findFirstToken(TokenTypes.LITERAL_PRIVATE) != null) {
                return "private";
            }
        }

        // Interfaces and annotation types: methods are implicitly public unless
        // they're private (allowed for interface default/static helper methods
        // since Java 9), which would already have been caught above.
        if (enclosingType.tokenType == TokenTypes.INTERFACE_DEF
                || enclosingType.tokenType == TokenTypes.ANNOTATION_DEF) {
            return "public";
        }

        // Enum constant bodies / regular classes with no explicit modifier.
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

    /**
     * Tracks an enclosing type declaration: its fully qualified (dotted, for
     * nested types) simple name and the AST token type it was declared with.
     */
    private record TypeContext(String qualifiedName, int tokenType) {
    }

}
