#!/usr/bin/env python3
"""Build script for Awesome Free GenAI.

Reads all YAML data files from data/ and generates:
  - README.md at the repo root (rendered from templates/README.md.j2)
  - dist/data.json for the frontend
  - Copies site/ files into dist/
"""

import json
import re
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
DIST_DIR = ROOT / "dist"
TEMPLATE_DIR = ROOT / "templates"

# Order in which categories appear (filename stems)
CATEGORY_ORDER = [
    "coding-agents",
    "research-agents",
    "browser-agents",
    "general-purpose-agents",
    "voice-agents",
    "workflow-agents",
    "sandbox-platforms",
    "fullstack-agents",
    "multimedia-generation",
    "personal-assistants",
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def classify_free_tier(free_tier: str) -> str:
    """Heuristically map a free_tier sentence to one of six canonical types."""
    if not free_tier:
        return "Free Plan"
    t = free_tier.lower()
    if "open source" in t or "open-source" in t or "mit license" in t or "apache" in t:
        return "Open Source"
    if "credit" in t:
        return "Free Credits"
    if "trial" in t:
        return "Free Trial"
    if "freemium" in t:
        return "Freemium"
    return "Free Plan"


def enrich_categories(categories: list[dict], stems: list[str]) -> list[dict]:
    """Add slug + per-agent slug & free_tier_type to each category dict."""
    enriched: list[dict] = []
    for cat, stem in zip(categories, stems):
        cat_slug = stem
        agents = []
        for agent in cat.get("agents", []) or []:
            a = dict(agent)
            a["slug"] = slugify(a.get("name", ""))
            a["category_slug"] = cat_slug
            a["category"] = cat.get("category", "")
            a["free_tier_type"] = classify_free_tier(a.get("free_tier", "") or "")
            agents.append(a)
        enriched.append({
            **cat,
            "slug": cat_slug,
            "agents": agents,
        })
    return enriched


def load_data() -> tuple[list[dict], list[str]]:
    """Load all YAML data files in the defined category order.

    Returns (categories, stems) so downstream consumers can use the filename
    stem as the canonical category slug.
    """
    categories: list[dict] = []
    stems: list[str] = []
    seen: set[str] = set()
    for stem in CATEGORY_ORDER:
        path = DATA_DIR / f"{stem}.yaml"
        if not path.exists():
            print(f"Warning: {path} not found, skipping.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        categories.append(data)
        stems.append(stem)
        seen.add(stem)
    # Also pick up any YAML files not in the explicit order
    for path in sorted(DATA_DIR.glob("*.yaml")):
        if path.stem in seen:
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        categories.append(data)
        stems.append(path.stem)
    return categories, stems


def generate_readme(categories: list[dict]) -> str:
    """Generate the full README.md content from the Jinja2 template."""
    total_tools = sum(len(cat.get("agents", [])) for cat in categories)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )

    template = env.get_template("README.md.j2")
    return template.render(
        categories=categories,
        total_tools=total_tools,
    )


def build_dist(categories: list[dict]) -> None:
    """Build the dist/ directory with frontend files and data.json."""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    # Copy site files
    if SITE_DIR.exists():
        for item in SITE_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, DIST_DIR / item.name)

    # Write combined data as JSON
    with open(DIST_DIR / "data.json", "w", encoding="utf-8") as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)


def main() -> None:
    print("Loading YAML data files...")
    categories, stems = load_data()

    if not categories:
        print("Error: No data files found in data/", file=sys.stderr)
        sys.exit(1)

    total = sum(len(c.get("agents", [])) for c in categories)
    print(f"Found {len(categories)} categories with {total} tools total.")

    print("Generating README.md...")
    readme = generate_readme(categories)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    print("Enriching data for the SPA...")
    enriched = enrich_categories(categories, stems)

    print("Building dist/...")
    build_dist(enriched)

    print("Done!")


if __name__ == "__main__":
    main()
