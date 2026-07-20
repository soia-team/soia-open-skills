#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || -z "${1:-}" ]]; then
  cat <<'EOF'
usage: init-project-baseline.sh <project-path>

Create a minimal AI-collaboration documentation baseline in an existing project
directory. The script refuses to overwrite any generated file.
EOF
  exit 0
fi

project_path="${1%/}"
if [[ ! -d "$project_path" ]]; then
  echo "[ERROR] project path not found: $project_path" >&2
  exit 1
fi

project_name="$(basename "$project_path")"
files=(
  "AGENTS.md"
  "docs/navigation.md"
  "docs/project-overview.md"
  "docs/product/README.md"
  "docs/changelog/README.md"
  "docs/ai-workspace/README.md"
  "docs/templates/README.md"
)
for file in "${files[@]}"; do
  if [[ -e "$project_path/$file" ]]; then
    echo "[ERROR] refusing to overwrite: $project_path/$file" >&2
    exit 2
  fi
done

mkdir -p "$project_path/docs/product" "$project_path/docs/changelog" \
  "$project_path/docs/ai-workspace" "$project_path/docs/templates"

cat > "$project_path/AGENTS.md" <<EOF
# AGENTS.md — $project_name

## Project rules

- Add the project's build, test, security, and release rules here.
- Keep project-specific instructions in this file or linked docs.
- Confirm before destructive, publishing, or external-state actions.
EOF
cat > "$project_path/docs/navigation.md" <<'EOF'
# Documentation navigation

- `project-overview.md` — purpose, architecture, and ownership
- `product/` — requirements and product references
- `changelog/` — release and change notes
- `ai-workspace/` — task records and handoffs
- `templates/` — reusable documentation templates
EOF
cat > "$project_path/docs/project-overview.md" <<EOF
# $project_name

- Purpose: <fill in>
- Owner: <fill in>
- Architecture: <fill in>
EOF
printf '# Product references\n\nStore requirement sources here.\n' > "$project_path/docs/product/README.md"
printf '# Changelog\n\nRecord concise, dated change notes here.\n' > "$project_path/docs/changelog/README.md"
printf '# AI workspace\n\nStore task records, evidence, and handoffs here.\n' > "$project_path/docs/ai-workspace/README.md"
printf '# Templates\n\nStore reusable project documentation templates here.\n' > "$project_path/docs/templates/README.md"

echo "[OK] created baseline for: $project_path"
