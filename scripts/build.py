#!/usr/bin/env python3
"""Build script for Awesome Free GenAI.

Reads all YAML data files from data/ and generates:
  - README.md at the repo root (rendered from templates/README.md.j2)
  - dist/data.json for the frontend
  - Copies site/ files into dist/
"""

import json
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
    "fullstack-agents",
    "multimedia-generation",
    "personal-assistants",
]


def load_data() -> list[dict]:
    """Load all YAML data files in the defined category order."""
    categories = []
    for stem in CATEGORY_ORDER:
        path = DATA_DIR / f"{stem}.yaml"
        if not path.exists():
            print(f"Warning: {path} not found, skipping.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        categories.append(data)
    # Also pick up any YAML files not in the explicit order
    for path in sorted(DATA_DIR.glob("*.yaml")):
        if path.stem not in CATEGORY_ORDER:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            categories.append(data)
    return categories


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
    categories = load_data()

    if not categories:
        print("Error: No data files found in data/", file=sys.stderr)
        sys.exit(1)

    total = sum(len(c.get("agents", [])) for c in categories)
    print(f"Found {len(categories)} categories with {total} tools total.")

    print("Generating README.md...")
    readme = generate_readme(categories)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    print("Building dist/...")
    build_dist(categories)

    print("Done!")


if __name__ == "__main__":
    main()
