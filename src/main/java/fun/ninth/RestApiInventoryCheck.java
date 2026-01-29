package fun.ninth;

import java.util.Objects;

import com.puppycrawl.tools.checkstyle.api.AbstractCheck;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

public class RestApiInventoryCheck extends AbstractCheck {

    private String currentPath = "";

    @Override
    public void visitToken(DetailAST detailAST) {
        switch (detailAST.getType()) {
            case TokenTypes.CLASS_DEF: {
                currentPath = extractPath(detailAST);
                break;
            }
            case TokenTypes.METHOD_DEF: {
                handleMethodDefinition(detailAST);
                break;
            }
        }
    }

    @Override
    public int[] getDefaultTokens() {
        return new int[]{TokenTypes.CLASS_DEF, TokenTypes.METHOD_DEF};
    }

    @Override
    public int[] getAcceptableTokens() {
        return getDefaultTokens();
    }

    @Override
    public int[] getRequiredTokens() {
        return getDefaultTokens();
    }

    private String extractPath(DetailAST detailAST) {
        DetailAST modifiers = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.MODIFIERS));
        for (DetailAST child = modifiers.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child.getType() != TokenTypes.ANNOTATION) {
                continue;
            }
            String name = getAnnotationName(child);
            if (name == null) {
                continue;
            }
            if (name.equals("Path")) {
                return getAnnotationValue(child);
            }
        }
        return "";
    }

    private String getAnnotationName(DetailAST detailAST) {
        DetailAST identifier = detailAST.findFirstToken(TokenTypes.IDENT);
        if (identifier != null) {
            return identifier.getText();
        }
        DetailAST dot = detailAST.findFirstToken(TokenTypes.DOT);
        return (dot != null) ? dot.getLastChild().getText() : null;
    }

    private String getAnnotationValue(DetailAST detailAST) {
        DetailAST expression = detailAST.findFirstToken(TokenTypes.EXPR);
        return (expression != null) ? expression.getFirstChild().getText().replace("\"", "") : "";
    }

    private String getAnnotationSummary(DetailAST detailAST) {
        for (DetailAST child = detailAST.findFirstToken(TokenTypes.ANNOTATION_MEMBER_VALUE_PAIR); child != null; child = child.getNextSibling()) {
            DetailAST identifier = child.findFirstToken(TokenTypes.IDENT);
            if (identifier == null) {
                continue;
            }
            if (child.getType() == TokenTypes.ANNOTATION_MEMBER_VALUE_PAIR && "summary".equals(identifier.getText())) {
                DetailAST expression = Objects.requireNonNull(child.findFirstToken(TokenTypes.EXPR));
                return expression.getFirstChild().getText().replace("\"", "");
            }
        }
        return "";
    }

    private void handleMethodDefinition(DetailAST detailAST) {
        DetailAST modifiers = Objects.requireNonNull(detailAST.findFirstToken(TokenTypes.MODIFIERS));
        String httpMethod = null;
        StringBuilder endpoint = new StringBuilder(currentPath);
        String summary = null;
        for (DetailAST child = modifiers.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child.getType() != TokenTypes.ANNOTATION) {
                continue;
            }
            String name = getAnnotationName(child);
            if (name == null) {
                continue;
            }
            switch (name) {
                case "GET":
                case "POST":
                case "PUT":
                case "DELETE":
                case "PATCH": {
                    httpMethod = name;
                    break;
                }
                case "Path": {
                    endpoint.append(getAnnotationValue(child));
                    break;
                }
                case "Operation": {
                    summary = getAnnotationSummary(child);
                    break;
                }
            }
        }
        if (httpMethod != null && !endpoint.isEmpty()) {
            System.out.printf("[DEBUG] [REST-API Inventory Check] %s %s \"%s\"%n", httpMethod, endpoint, summary);
        }
    }

}