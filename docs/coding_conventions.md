# SDMS Coding Conventions

These conventions apply to every file in `src/` and `tests/`. They exist so
that any team member can read any module and find what they need without
guessing.

## Language and tooling

* Python 3.11 or newer.
* Formatter: `black` with the default 88-character line length.
* Linter: `ruff` with the `E`, `F`, `I`, `B`, and `UP` rule sets.
* Test runner: `pytest`.

## Naming

| Element                  | Convention            | Example                |
| ------------------------ | --------------------- | ---------------------- |
| Modules and packages     | `snake_case`          | `audit_logger.py`      |
| Classes                  | `PascalCase`          | `SecurityProxy`        |
| Functions and methods    | `snake_case`          | `validate_otp`         |
| Constants                | `UPPER_SNAKE_CASE`    | `DEFAULT_TTL_SECONDS`  |
| Private members          | leading underscore    | `_entries`, `_lock`    |
| Test files               | `test_<module>.py`    | `test_security_proxy.py` |

UML class names from the SDS map to Python class names directly. UML
attribute names like `userID` become `user_id` in Python so the code stays
idiomatic while remaining traceable.

## Commenting style

* Every module starts with a docstring that says what the module does and
  which SDS element it implements.
* Every public class and method has a one-line docstring at minimum. Where
  the class implements a design pattern or expresses a specific OOP
  principle, the docstring calls that out so the marker can find it.
* Inline comments explain *why*, not *what*. The code already shows what.
* Avoid comment blocks that restate the function signature.

## Commit message format

Commits follow the [Conventional Commits](https://www.conventionalcommits.org/) style:

```
<type>(<scope>): <short summary in the imperative>

<optional body explaining the why>
```

Allowed types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`.

Examples:

```
feat(patterns): add SecurityProxy with rate limiting and audit hooks
test(audit): cover singleton identity and archive_logs reset
docs(conventions): document branch naming and PR review checklist
```

The summary line is 72 characters or fewer, lower case after the colon, no
trailing full stop.

## Branching

* `main` is always green: tests pass on every push.
* Feature branches: `feat/<short-name>` or `fix/<short-name>`.
* Pull requests need at least one peer review before merge.

## Definition of done

A change is "done" when:

1. The code compiles and `pytest` is green.
2. New behaviour is covered by at least one test.
3. The relevant SDS class or pattern is referenced in a docstring.
4. The commit message follows the format above.
