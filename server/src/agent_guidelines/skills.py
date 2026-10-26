"""Load, validate, match and search the skills directory.

Each guideline is a directory ``skills/<name>/`` with a ``SKILL.md`` (YAML frontmatter
plus Markdown) and optional extra files such as ``references/*.md``.
``name`` and ``description`` follow the Agent Skills format, so the directories work
unchanged as Copilot/Claude skills. Our own fields live under ``metadata``.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from wcmatch import glob as wcglob

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
LINK_RE = re.compile(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)")
GLOB_FLAGS = wcglob.GLOBSTAR | wcglob.DOTGLOB | wcglob.BRACE


@dataclass
class Skill:
    name: str
    description: str
    area: str
    applies_to: list[str]
    tags: list[str]
    body: str  # SKILL.md without frontmatter
    files: dict[str, str]  # relative path -> content, including SKILL.md

    @property
    def reference_files(self) -> list[str]:
        return [f for f in self.files if f != "SKILL.md"]


@dataclass
class Catalog:
    version: str  # content hash of every skill file; changes on any edit
    skills: list[Skill] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def get(self, name: str) -> Skill | None:
        return next((s for s in self.skills if s.name == name), None)

    @property
    def areas(self) -> list[str]:
        return sorted({s.area for s in self.skills})


def _split_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _read_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts) or not p.is_file():
            continue
        files[rel.as_posix()] = p.read_text(encoding="utf-8")
    return files


def _validate_frontmatter(dirname: str, data: object) -> tuple[dict | None, list[str]]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return None, [f"{dirname}/SKILL.md: frontmatter must be a YAML mapping"]
    name = data.get("name")
    desc = data.get("description")
    meta = data.get("metadata")
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
        errs.append(f"{dirname}/SKILL.md: name must be lowercase letters, digits and single hyphens (max 64)")
    elif name != dirname:
        errs.append(f"{dirname}/SKILL.md: name '{name}' must equal directory name '{dirname}'")
    if not isinstance(desc, str) or not desc.strip():
        errs.append(f"{dirname}/SKILL.md: description is required")
    elif len(desc) > 1024:
        errs.append(f"{dirname}/SKILL.md: description is longer than 1024 characters")
    if not isinstance(meta, dict) or not str(meta.get("area") or "").strip():
        errs.append(f"{dirname}/SKILL.md: metadata.area is required")
    return (None if errs else data), errs


def load_catalog(skills_dir: str | Path) -> Catalog:
    """Read the whole skills directory. Cheap for tens of skills; called per request."""
    root = Path(skills_dir)
    if not root.is_dir():
        return Catalog(version="none", errors=[f"Skills directory not found: {root}"])

    digest = hashlib.sha256()
    catalog = Catalog(version="")

    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        files = _read_files(d)
        for rel, content in files.items():
            digest.update(f"{d.name}/{rel}\0{content}\0".encode())

        raw = files.get("SKILL.md")
        if raw is None:
            catalog.errors.append(f"{d.name}: missing SKILL.md")
            continue
        m = FRONTMATTER_RE.match(raw)
        if not m:
            catalog.errors.append(f"{d.name}/SKILL.md: missing '---' YAML frontmatter")
            continue
        try:
            data = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            catalog.errors.append(f"{d.name}/SKILL.md: invalid YAML ({e})")
            continue
        fm, errs = _validate_frontmatter(d.name, data)
        if errs:
            catalog.errors.extend(errs)
            continue
        body = m.group(2).strip()

        # Relative links must resolve to files inside the skill directory
        for target in LINK_RE.findall(body):
            path = posixpath.normpath(target.split("#")[0])
            if path and path not in files:
                catalog.errors.append(f"{d.name}/SKILL.md: broken link '{target}'")

        meta = fm["metadata"]
        catalog.skills.append(
            Skill(
                name=fm["name"],
                description=" ".join(fm["description"].split()),
                area=str(meta["area"]).strip(),
                applies_to=_split_list(meta.get("applies_to")),
                tags=_split_list(meta.get("tags")),
                body=body,
                files=files,
            )
        )

    catalog.version = digest.hexdigest()[:12]
    return catalog


def match_files(catalog: Catalog, paths: list[str]) -> list[Skill]:
    norm = [p.replace("\\", "/").removeprefix("./") for p in paths]
    return [
        s
        for s in catalog.skills
        if any(wcglob.globmatch(p, s.applies_to, flags=GLOB_FLAGS) for p in norm) and s.applies_to
    ]


def search(catalog: Catalog, query: str, limit: int = 8) -> list[Skill]:
    terms = [t for t in query.lower().split() if t]
    scored: list[tuple[int, Skill]] = []
    for s in catalog.skills:
        head = f"{s.name} {s.description} {' '.join(s.tags)}".lower()
        everything = f"{head} {' '.join(s.files.values())}".lower()
        score = sum(everything.count(t) + (5 if t in head else 0) for t in terms)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [s for _, s in scored[:limit]]


def render(skills: list[Skill], version: str) -> str:
    if not skills:
        return f"No matching guidelines.\n\n(guidelines@{version})"
    parts = []
    for s in skills:
        refs = f"\n\nReference files (get_guideline_file): {', '.join(s.reference_files)}" if s.reference_files else ""
        parts.append(f'<guideline name="{s.name}" area="{s.area}">\n{s.body}{refs}\n</guideline>')
    return "\n\n".join(parts) + f"\n\n(guidelines@{version}; cite guideline names when applying or reviewing against these rules)"
