"""CI check: every skill directory must load cleanly.

Usage: agent-guidelines-validate [skills_dir]   (default: ../skills)
"""

from __future__ import annotations

import sys

from .skills import load_catalog


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    skills_dir = argv[0] if argv else "../skills"
    c = load_catalog(skills_dir)
    for s in c.skills:
        globs = f" -> {', '.join(s.applies_to)}" if s.applies_to else ""
        refs = f" (+{len(s.reference_files)} reference files)" if s.reference_files else ""
        print(f"ok   {s.name} ({s.area}){globs}{refs}")
    for e in c.errors:
        print(f"FAIL {e}", file=sys.stderr)
    print(f"\n{len(c.skills)} skills, {len(c.errors)} errors, version {c.version}")
    return 1 if c.errors else 0


if __name__ == "__main__":
    sys.exit(main())
