"""The naming rule of `docs/technical/conventions.md`, made executable.

A function is an action: its name starts with a verb. Written in prose the rule
drifts on the first hurried commit — here a noun-named function fails the suite.
"""

import ast
from pathlib import Path
from typing import Final

_SRC: Final = Path(__file__).resolve().parents[1] / "src"

# The verbs the project actually speaks. Adding one is a deliberate act: it means the
# codebase gained a kind of action, not that a nominal name needed a home.
_VERBS: Final[frozenset[str]] = frozenset(
    {
        # queries a store
        "find",
        "list",
        "search",
        "load",
        "get",  # plain accessor over a loaded field only — never in front of a query
        # derives from what it already holds
        "build",
        "compute",
        "format",
        "render",
        "classify",
        "clamp",
        "keep",
        "select",
        "sort",
        "group",
        "merge",
        "count",
        "fold",
        "normalise",
        "clean",
        "escape",
        "split",
        "extract",
        "assess",  # measures a listing against a reference
        "annotate",  # returns copies carrying a display-only field
        "propose",  # derives a change the hunter must still confirm
        # resolves an indirection / reads a value
        "read",
        "resolve",
        "pick",
        "require",
        # reads scraped text
        "parse",
        "detect",
        # changes state
        "save",
        "migrate",  # moves stored data into the shape a newer schema reads
        "update",
        "delete",
        "apply",
        "sync",
        "mark",
        "purge",
        "backfill",
        "seed",
        "download",
        "set",
        "invalidate",
        "add",
        "reject",
        "dismiss",  # the hunter's judgement on a home (ADR-0009)
        "restore",  # ...and taking it back
        "ignore",  # a null object's no-op sink (`ignore_progress`)
        # creates and returns
        "create",
        "make",
        # does the work / drives IO
        "execute",
        "run",
        "do",
        "fetch",
        "crawl",
        "gather",
        "paginate",
        "enrich",
        "collect",
        "geocode",
        "expand",
        "notify",
        "ask",
        "send",
        "print",
        "log",
        "connect",
        "close",
        "open",
        "ensure",
        "intercept",
        "setup",
        "start",
        "stop",
        "cancel",
        "trigger",
        "watch",
        "review",
        "serve",
        "sleep",
        "await",
        # predicates
        "is",
        "has",
        "can",
        "should",
        "matches",
    }
)

# Names a framework owns, and named constructors whose noun *is* the value produced.
_EXEMPT_NAMES: Final[frozenset[str]] = frozenset({"lifespan", "on_response", "unknown", "ground"})

# `to_…` / `from_…` / `with_…` conversions read as actions and keep their idiom.
_EXEMPT_PREFIXES: Final[tuple[str, ...]] = ("to_", "from_", "with_", "up_to")
_EXEMPT_INFIXES: Final[tuple[str, ...]] = ("_to_", "_from_")


def _collect_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every def in the module except properties and dunders — those are things, not actions."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("__")
        and not any("property" in ast.unparse(d) for d in node.decorator_list)
    ]


def _is_exempt(name: str) -> bool:
    return (
        name in _EXEMPT_NAMES
        or name.lstrip("_").startswith(_EXEMPT_PREFIXES)
        or any(infix in name for infix in _EXEMPT_INFIXES)
    )


def find_nominal_functions() -> list[str]:
    """`file:line:name` for every src function whose name doesn't start with a verb.

    O(n) in AST nodes, one set lookup per function name.
    """
    offenders = []
    for path in sorted(_SRC.rglob("*.py")):
        for node in _collect_functions(ast.parse(path.read_text(encoding="utf-8"))):
            if _is_exempt(node.name):
                continue
            if node.name.lstrip("_").split("_")[0] not in _VERBS:
                offenders.append(f"{path.relative_to(_SRC)}:{node.lineno}:{node.name}")
    return offenders


def test_every_function_name_starts_with_a_verb() -> None:
    # Arrange / Act
    offenders = find_nominal_functions()

    # Assert
    assert not offenders, (
        "A function is an action — these names are nominal:\n  "
        + "\n  ".join(offenders)
        + "\nRename with a verb (see docs/technical/conventions.md § Nommage), or add the"
        " verb to _VERBS if the codebase genuinely gained a new kind of action."
    )
