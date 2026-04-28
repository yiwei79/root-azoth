#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────
# Azoth Installer — macOS / Linux
# Installs the Azoth agentic toolkit into the current project.
# Usage: bash /path/to/azoth/install.sh
# ─────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(pwd)"

read_azoth_version() {
    local manifest="$SCRIPT_DIR/azoth.yaml"
    if [ -f "$manifest" ]; then
        local version
        version="$(sed -n 's/^version:[[:space:]]*//p' "$manifest" | head -n 1)"
        if [ -n "$version" ]; then
            printf '%s\n' "$version"
            return
        fi
    fi
    printf '%s\n' "0.1.0"
}

AZOTH_VERSION="$(read_azoth_version)"

# ── Colors ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[azoth]${NC} $1"; }
ok()    { echo -e "${GREEN}[azoth]${NC} $1"; }
warn()  { echo -e "${YELLOW}[azoth]${NC} $1"; }
err()   { echo -e "${RED}[azoth]${NC} $1" >&2; }

# ── Pre-flight checks ──────────────────────────────────────────
if [ "$SCRIPT_DIR" = "$TARGET_DIR" ]; then
    err "Cannot install Azoth into its own repository."
    err "Usage: cd /your/project && bash /path/to/azoth/install.sh"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/kernel" ]; then
    err "Azoth kernel not found at $SCRIPT_DIR/kernel"
    err "Did you run the bootstrap first? See docs/DAY0_TUTORIAL.md"
    exit 1
fi

# ── Banner ──────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           🧪 AZOTH — Project Setup              ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║  Version: ${AZOTH_VERSION}                              ║${NC}"
echo -e "${CYAN}║  Source:  ${SCRIPT_DIR}${NC}"
echo -e "${CYAN}║  Target:  ${TARGET_DIR}${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Detect platforms ────────────────────────────────────────────
PLATFORMS=""

if [ -d ".claude" ] || command -v claude &>/dev/null; then
    PLATFORMS="${PLATFORMS}claude "
    info "Detected: Claude Code"
fi

if [ -f "opencode.jsonc" ] || [ -d ".opencode" ] || command -v opencode &>/dev/null; then
    PLATFORMS="${PLATFORMS}opencode "
    info "Detected: OpenCode"
fi

if [ -d ".codex" ] || command -v codex &>/dev/null; then
    PLATFORMS="${PLATFORMS}codex "
    info "Detected: Codex"
fi

if [ -d ".github" ] || [ -f ".github/copilot-instructions.md" ]; then
    PLATFORMS="${PLATFORMS}copilot "
    info "Detected: GitHub Copilot"
fi

if [ -z "$PLATFORMS" ]; then
    info "No specific platform detected. Defaulting to Claude Code."
    PLATFORMS="claude"
fi

# ── Detect project ──────────────────────────────────────────────
PROJECT_NAME="$(basename "$TARGET_DIR")"
LANGUAGE="unknown"
FORMATTER="unknown"
TEST_FRAMEWORK="unknown"
SOURCE_DIR="src"
TEST_DIR="tests"

if [ -f "package.json" ]; then
    LANGUAGE="JavaScript/TypeScript"
    FORMATTER="prettier"
    TEST_FRAMEWORK="jest"
    SOURCE_DIR="src"
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
    LANGUAGE="Python"
    FORMATTER="ruff format + ruff check"
    TEST_FRAMEWORK="pytest"
    SOURCE_DIR="src"
elif [ -f "go.mod" ]; then
    LANGUAGE="Go"
    FORMATTER="gofmt"
    TEST_FRAMEWORK="go test"
    SOURCE_DIR="."
elif [ -f "Cargo.toml" ]; then
    LANGUAGE="Rust"
    FORMATTER="rustfmt"
    TEST_FRAMEWORK="cargo test"
    SOURCE_DIR="src"
fi

info "Project: $PROJECT_NAME ($LANGUAGE)"

# ── Choose setup level ──────────────────────────────────────────
echo ""
echo "Choose your setup:"
echo "  [1] Minimal  — Kernel only (bootloader + trust)"
echo "  [2] Standard — Kernel + core skills + T1 agents"
echo "  [3] Full     — Everything (skills + all agents + research + meta)"
echo ""
read -rp "Selection [1/2/3] (default: 2): " SETUP_LEVEL
SETUP_LEVEL="${SETUP_LEVEL:-2}"

case "$SETUP_LEVEL" in
    1) INSTALL_SKILLS=false; INSTALL_AGENTS=false ;;
    2) INSTALL_SKILLS=true;  INSTALL_AGENTS="tier1" ;;
    3) INSTALL_SKILLS=true;  INSTALL_AGENTS="all" ;;
    *)
        warn "Invalid selection, using Standard (2)"
        INSTALL_SKILLS=true; INSTALL_AGENTS="tier1"
        ;;
esac

# ── Step 1: Deploy kernel ──────────────────────────────────────
info "Deploying kernel..."

mkdir -p ".azoth/memory" ".azoth/telemetry"

# Copy kernel governance docs (read-only reference; lexicographic order matches GOVERNANCE §4)
mkdir -p ".azoth/kernel"
cp "$SCRIPT_DIR/kernel/BOOTLOADER.md" ".azoth/kernel/"
cp "$SCRIPT_DIR/kernel/GOVERNANCE.md" ".azoth/kernel/"
cp "$SCRIPT_DIR/kernel/PROMOTION_RUBRIC.md" ".azoth/kernel/"
cp "$SCRIPT_DIR/kernel/TRUST_CONTRACT.md" ".azoth/kernel/"

ok "Kernel deployed to .azoth/kernel/"

# ── Step 2: Generate CLAUDE.md ─────────────────────────────────
info "Generating CLAUDE.md..."

INSTALLED_SKILLS="none"
INSTALLED_AGENTS_STR="none"
INSTALLED_PIPELINES="auto, deliver, deliver-full"

if [ "$INSTALL_SKILLS" = true ]; then
    INSTALLED_SKILLS="context-map, structured-autonomy-plan, agentic-eval, remember, prompt-engineer"
fi

case "$INSTALL_AGENTS" in
    tier1) INSTALLED_AGENTS_STR="architect, planner, builder, reviewer" ;;
    all)   INSTALLED_AGENTS_STR="architect, planner, builder, reviewer, researcher, research-orchestrator, prompt-engineer, evaluator, agent-crafter, context-architect" ;;
esac

GITHUB_USER="${GITHUB_USER:-yourusername}"

sed -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
    -e "s|{{LANGUAGE}}|$LANGUAGE|g" \
    -e "s|{{DESCRIPTION}}|A project powered by Azoth|g" \
    -e "s|{{SOURCE_DIR}}|$SOURCE_DIR|g" \
    -e "s|{{TEST_DIR}}|$TEST_DIR|g" \
    -e "s|{{FORMATTER}}|$FORMATTER|g" \
    -e "s|{{TEST_FRAMEWORK}}|$TEST_FRAMEWORK|g" \
    -e "s|{{AZOTH_VERSION}}|$AZOTH_VERSION|g" \
    -e "s|{{INSTALLED_SKILLS}}|$INSTALLED_SKILLS|g" \
    -e "s|{{INSTALLED_AGENTS}}|$INSTALLED_AGENTS_STR|g" \
    -e "s|{{INSTALLED_PIPELINES}}|$INSTALLED_PIPELINES|g" \
    -e "s|{{GITHUB_USER}}|$GITHUB_USER|g" \
    "$SCRIPT_DIR/kernel/templates/CLAUDE.md.template" > "CLAUDE.md"

ok "CLAUDE.md generated"

# ── Step 3: Platform-specific files ────────────────────────────
for platform in $PLATFORMS; do
    case "$platform" in
        claude)
            info "Setting up Claude Code..."
            mkdir -p ".claude/commands" ".claude/agents"
            sed -e "s|{{AZOTH_VERSION}}|$AZOTH_VERSION|g" \
                "$SCRIPT_DIR/kernel/templates/settings.json.template" > ".claude/settings.json"
            ok "Claude Code configured (.claude/)"
            ;;
        opencode)
            info "Setting up OpenCode..."
            mkdir -p ".opencode/agent" ".opencode/command"
            sed -e "s|{{MODEL}}|claude-sonnet-4-20250514|g" \
                "$SCRIPT_DIR/kernel/templates/platform-adapters/opencode/opencode.jsonc.template" > "opencode.jsonc"
            ok "OpenCode configured (.opencode/, opencode.jsonc)"
            ;;
        codex)
            info "Setting up Codex..."
            mkdir -p ".codex/agents" ".codex/hooks"
            cp "$SCRIPT_DIR/kernel/templates/platform-adapters/codex/config.toml.template" ".codex/config.toml"
            cp "$SCRIPT_DIR/kernel/templates/platform-adapters/codex/hooks.json.template" ".codex/hooks.json"
            cp "$SCRIPT_DIR/kernel/templates/platform-adapters/codex/user_prompt_submit_router.py.template" \
                ".codex/hooks/user_prompt_submit_router.py"
            ok "Codex configured (.codex/)"
            ;;
        copilot)
            info "Setting up GitHub Copilot..."
            mkdir -p ".github/agents" ".github/prompts"
            sed -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
                "$SCRIPT_DIR/kernel/templates/copilot-instructions.md.template" > ".github/copilot-instructions.md"
            ok "Copilot configured (.github/)"
            ;;
    esac
done

# ── Step 4: Skills ─────────────────────────────────────────────
if [ "$INSTALL_SKILLS" = true ] && [ -d "$SCRIPT_DIR/skills" ]; then
    info "Installing skills..."
    mkdir -p "skills"
    cp -r "$SCRIPT_DIR/skills/"* "skills/" 2>/dev/null || warn "No skills found to install"
    if [[ " $PLATFORMS " == *" codex "* ]]; then
        mkdir -p ".agents/skills"
        cp -r "$SCRIPT_DIR/skills/"* ".agents/skills/" 2>/dev/null || warn "No Codex skills found to install"
    fi
    ok "Skills installed"
elif [ "$INSTALL_SKILLS" = true ]; then
    warn "Skills directory not found in Azoth source (Phase 2 not yet built)"
fi

# ── Step 5: Agents ─────────────────────────────────────────────
if [ "$INSTALL_AGENTS" != false ] && [ -d "$SCRIPT_DIR/agents" ]; then
    info "Installing agents..."
    mkdir -p "agents"
    if [ "$INSTALL_AGENTS" = "tier1" ]; then
        cp -r "$SCRIPT_DIR/agents/tier1-core/"* "agents/" 2>/dev/null || warn "T1 agents not yet built"
    else
        cp -r "$SCRIPT_DIR/agents/"* "agents/" 2>/dev/null || warn "Agents not yet built"
    fi
    ok "Agents installed"
elif [ "$INSTALL_AGENTS" != false ]; then
    warn "Agents directory not found in Azoth source (Phase 3 not yet built)"
fi

# ── Step 6: Initialize memory ──────────────────────────────────
info "Initializing memory system..."

if [ ! -f ".azoth/memory/episodes.jsonl" ]; then
    touch ".azoth/memory/episodes.jsonl"
fi

if [ ! -f ".azoth/memory/patterns.yaml" ]; then
    echo "# Azoth Semantic Memory (M2)" > ".azoth/memory/patterns.yaml"
    echo "# Promoted from M3 episodes via Promotion Rubric" >> ".azoth/memory/patterns.yaml"
    echo "patterns: []" >> ".azoth/memory/patterns.yaml"
fi

# Generate bootloader state
sed -e "s|operate|1|g" \
    "$SCRIPT_DIR/kernel/templates/bootloader-state.md.template" > ".azoth/bootloader-state.md" 2>/dev/null \
    || cp "$SCRIPT_DIR/kernel/templates/bootloader-state.md.template" ".azoth/bootloader-state.md"

ok "Memory system initialized"

# ── Step 7: Generate kernel checksums (GOVERNANCE §4 — four files, lex order; D42 mirror) ─
# Authoritative toolkit paths are kernel/*.md; consumer read-only mirror is .azoth/kernel/ (four §4 files)
info "Generating kernel checksums..."
if command -v sha256sum &>/dev/null; then
    sha256sum \
        .azoth/kernel/BOOTLOADER.md \
        .azoth/kernel/GOVERNANCE.md \
        .azoth/kernel/PROMOTION_RUBRIC.md \
        .azoth/kernel/TRUST_CONTRACT.md \
        > .azoth/kernel-checksums.sha256
elif command -v shasum &>/dev/null; then
    shasum -a 256 \
        .azoth/kernel/BOOTLOADER.md \
        .azoth/kernel/GOVERNANCE.md \
        .azoth/kernel/PROMOTION_RUBRIC.md \
        .azoth/kernel/TRUST_CONTRACT.md \
        > .azoth/kernel-checksums.sha256
fi
ok "Kernel integrity baseline established"

# ── Step 8: Gitignore runtime state ────────────────────────────
if [ -f ".gitignore" ]; then
    if ! grep -q ".azoth/telemetry" ".gitignore" 2>/dev/null; then
        echo "" >> ".gitignore"
        echo "# Azoth runtime state" >> ".gitignore"
        echo ".azoth/telemetry/" >> ".gitignore"
        echo ".azoth/session-orientation.txt" >> ".gitignore"
        echo ".azoth/bootloader-state.md" >> ".gitignore"
        echo ".azoth/kernel-checksums.sha256" >> ".gitignore"
        echo ".azoth/proposals/" >> ".gitignore"
    fi
else
    cat > ".gitignore" << 'GITIGNORE'
# Azoth runtime state
.azoth/telemetry/
.azoth/session-orientation.txt
.azoth/bootloader-state.md
.azoth/kernel-checksums.sha256
.azoth/proposals/
GITIGNORE
fi

if [ -f ".gitignore" ] && ! grep -qF ".azoth/proposals/" ".gitignore" 2>/dev/null; then
    echo ".azoth/proposals/" >> ".gitignore"
fi

ok "Gitignore updated"

# ── Step 9: Generate manifest ──────────────────────────────────
platforms_manifest_yaml() {
    local platform
    for platform in $PLATFORMS; do
        printf '  - %s\n' "$platform"
    done
}

PLATFORMS_YAML="$(platforms_manifest_yaml)"

cat > "azoth.yaml" << MANIFEST
name: azoth
version: $AZOTH_VERSION
project: $PROJECT_NAME
installed:
  kernel: true
  skills: $INSTALL_SKILLS
  agents: $INSTALL_AGENTS
platforms:
$PLATFORMS_YAML
MANIFEST

ok "Manifest generated (azoth.yaml)"

# ── Summary ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        🧪 AZOTH — Installation Complete         ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Project: $PROJECT_NAME${NC}"
echo -e "${GREEN}║  Kernel:  deployed to .azoth/kernel/             ║${NC}"
echo -e "${GREEN}║  Memory:  initialized (.azoth/memory/)           ║${NC}"
echo -e "${GREEN}║  Platforms: ${PLATFORMS}${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Next: Open your AI coding tool and start a      ║${NC}"
echo -e "${GREEN}║  session. The agent will read CLAUDE.md and      ║${NC}"
echo -e "${GREEN}║  boot automatically.                             ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
