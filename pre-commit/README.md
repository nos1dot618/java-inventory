> Git-Pre-Commit hook for java-projects; utilizes [checkstyle](https://github.com/checkstyle/checkstyle/) for linting.

---

## Getting started

### Windows

Navigate to your project, then run the following:

```powershell
irm https://raw.githubusercontent.com/nos1dot618/git-hook-java/refs/heads/master/SETUP.ps1 | iex
```

## About

This project uses a customized version of the ["Google Java Style Guide"](https://github.com/checkstyle/checkstyle/blob/master/src/main/resources/google_checks.xml) for code-style-linting. The following modifications have been made to the original style guide:

1. Do not ignore empty statements.
2. Warn on fall-through in switch-case statements.
3. Ignore fall-through in the final switch-case block.
4. Suggest variables that can be declared as `final`.
5. Set the indentation offset to `4` spaces.
6. Warn about unused local-variables.
7. Enforce a custom import order.
8. Warn about redundant and unused imports.
9. Enforce strict single-space separation.
10. Warn when newline conventions are violated.

## References

1. CheckStyle Documentation: <https://checkstyle.org/index.html>