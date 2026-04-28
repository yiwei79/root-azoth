# ─────────────────────────────────────────────────────────────────
# Azoth Installer — Windows (PowerShell)
# Installs the Azoth agentic toolkit into the current project.
# Usage: pwsh /path/to/azoth/install.ps1
# ─────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$TARGET_DIR = Get-Location

function Get-AzothVersion {
    $manifest = Join-Path $SCRIPT_DIR "azoth.yaml"
    if (Test-Path $manifest) {
        $line = Get-Content $manifest | Where-Object { $_ -match '^version:\s*(.+)$' } | Select-Object -First 1
        if ($line -match '^version:\s*(.+)$') {
            return $Matches[1].Trim()
        }
    }
    return "0.1.0"
}

$AZOTH_VERSION = Get-AzothVersion

# ── Helpers ─────────────────────────────────────────────────────
function Info($msg)  { Write-Host "[azoth] $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "[azoth] $msg" -ForegroundColor Green }
function Warn($msg)  { Write-Host "[azoth] $msg" -ForegroundColor Yellow }
function Err($msg)   { Write-Host "[azoth] $msg" -ForegroundColor Red }

# ── Pre-flight checks ──────────────────────────────────────────
if ($SCRIPT_DIR -eq $TARGET_DIR) {
    Err "Cannot install Azoth into its own repository."
    Err "Usage: cd \your\project; pwsh \path\to\azoth\install.ps1"
    exit 1
}

if (-not (Test-Path "$SCRIPT_DIR\kernel")) {
    Err "Azoth kernel not found at $SCRIPT_DIR\kernel"
    Err "Did you run the bootstrap first? See docs\DAY0_TUTORIAL.md"
    exit 1
}

# ── Banner ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           🧪 AZOTH — Project Setup              ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Version: $AZOTH_VERSION" -ForegroundColor Cyan
Write-Host "║  Source:  $SCRIPT_DIR" -ForegroundColor Cyan
Write-Host "║  Target:  $TARGET_DIR" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Detect platforms ────────────────────────────────────────────
$PLATFORMS = @()

if ((Test-Path ".claude") -or (Get-Command claude -ErrorAction SilentlyContinue)) {
    $PLATFORMS += "claude"
    Info "Detected: Claude Code"
}

if ((Test-Path "opencode.jsonc") -or (Test-Path ".opencode") -or (Get-Command opencode -ErrorAction SilentlyContinue)) {
    $PLATFORMS += "opencode"
    Info "Detected: OpenCode"
}

if ((Test-Path ".codex") -or (Get-Command codex -ErrorAction SilentlyContinue)) {
    $PLATFORMS += "codex"
    Info "Detected: Codex"
}

if ((Test-Path ".github") -or (Test-Path ".github\copilot-instructions.md")) {
    $PLATFORMS += "copilot"
    Info "Detected: GitHub Copilot"
}

if ($PLATFORMS.Count -eq 0) {
    Info "No specific platform detected. Defaulting to Claude Code."
    $PLATFORMS = @("claude")
}

# ── Detect project ──────────────────────────────────────────────
$PROJECT_NAME = Split-Path -Leaf $TARGET_DIR
$LANGUAGE = "unknown"
$FORMATTER = "unknown"
$TEST_FRAMEWORK = "unknown"
$SOURCE_DIR = "src"
$TEST_DIR = "tests"

if (Test-Path "package.json") {
    $LANGUAGE = "JavaScript/TypeScript"; $FORMATTER = "prettier"; $TEST_FRAMEWORK = "jest"
} elseif ((Test-Path "pyproject.toml") -or (Test-Path "setup.py") -or (Test-Path "requirements.txt")) {
    $LANGUAGE = "Python"; $FORMATTER = "ruff format + ruff check"; $TEST_FRAMEWORK = "pytest"
} elseif (Test-Path "go.mod") {
    $LANGUAGE = "Go"; $FORMATTER = "gofmt"; $TEST_FRAMEWORK = "go test"; $SOURCE_DIR = "."
} elseif (Test-Path "Cargo.toml") {
    $LANGUAGE = "Rust"; $FORMATTER = "rustfmt"; $TEST_FRAMEWORK = "cargo test"
}

Info "Project: $PROJECT_NAME ($LANGUAGE)"

# ── Choose setup level ──────────────────────────────────────────
Write-Host ""
Write-Host "Choose your setup:"
Write-Host "  [1] Minimal  — Kernel only (bootloader + trust)"
Write-Host "  [2] Standard — Kernel + core skills + T1 agents"
Write-Host "  [3] Full     — Everything (skills + all agents + research + meta)"
Write-Host ""
$SETUP_LEVEL = Read-Host "Selection [1/2/3] (default: 2)"
if (-not $SETUP_LEVEL) { $SETUP_LEVEL = "2" }

$INSTALL_SKILLS = $false
$INSTALL_AGENTS = $false

switch ($SETUP_LEVEL) {
    "1" { $INSTALL_SKILLS = $false; $INSTALL_AGENTS = $false }
    "2" { $INSTALL_SKILLS = $true;  $INSTALL_AGENTS = "tier1" }
    "3" { $INSTALL_SKILLS = $true;  $INSTALL_AGENTS = "all" }
    default {
        Warn "Invalid selection, using Standard (2)"
        $INSTALL_SKILLS = $true; $INSTALL_AGENTS = "tier1"
    }
}

# ── Step 1: Deploy kernel ──────────────────────────────────────
Info "Deploying kernel..."

New-Item -ItemType Directory -Force -Path ".azoth\memory" | Out-Null
New-Item -ItemType Directory -Force -Path ".azoth\telemetry" | Out-Null
New-Item -ItemType Directory -Force -Path ".azoth\kernel" | Out-Null

Copy-Item "$SCRIPT_DIR\kernel\BOOTLOADER.md" ".azoth\kernel\"
Copy-Item "$SCRIPT_DIR\kernel\TRUST_CONTRACT.md" ".azoth\kernel\"
Copy-Item "$SCRIPT_DIR\kernel\GOVERNANCE.md" ".azoth\kernel\"
Copy-Item "$SCRIPT_DIR\kernel\PROMOTION_RUBRIC.md" ".azoth\kernel\"

Ok "Kernel deployed to .azoth\kernel\"

# ── Step 2: Generate CLAUDE.md ─────────────────────────────────
Info "Generating CLAUDE.md..."

$INSTALLED_SKILLS_STR = "none"
$INSTALLED_AGENTS_STR = "none"
$INSTALLED_PIPELINES = "auto, deliver, deliver-full"

if ($INSTALL_SKILLS) {
    $INSTALLED_SKILLS_STR = "context-map, structured-autonomy-plan, agentic-eval, remember, prompt-engineer"
}

switch ($INSTALL_AGENTS) {
    "tier1" { $INSTALLED_AGENTS_STR = "architect, planner, builder, reviewer" }
    "all"   { $INSTALLED_AGENTS_STR = "architect, planner, builder, reviewer, researcher, research-orchestrator, prompt-engineer, evaluator, agent-crafter, context-architect" }
}

$GITHUB_USER = if ($env:GITHUB_USER) { $env:GITHUB_USER } else { "yourusername" }

$template = Get-Content "$SCRIPT_DIR\kernel\templates\CLAUDE.md.template" -Raw
$template = $template -replace '\{\{PROJECT_NAME\}\}', $PROJECT_NAME
$template = $template -replace '\{\{LANGUAGE\}\}', $LANGUAGE
$template = $template -replace '\{\{DESCRIPTION\}\}', "A project powered by Azoth"
$template = $template -replace '\{\{SOURCE_DIR\}\}', $SOURCE_DIR
$template = $template -replace '\{\{TEST_DIR\}\}', $TEST_DIR
$template = $template -replace '\{\{FORMATTER\}\}', $FORMATTER
$template = $template -replace '\{\{TEST_FRAMEWORK\}\}', $TEST_FRAMEWORK
$template = $template -replace '\{\{AZOTH_VERSION\}\}', $AZOTH_VERSION
$template = $template -replace '\{\{INSTALLED_SKILLS\}\}', $INSTALLED_SKILLS_STR
$template = $template -replace '\{\{INSTALLED_AGENTS\}\}', $INSTALLED_AGENTS_STR
$template = $template -replace '\{\{INSTALLED_PIPELINES\}\}', $INSTALLED_PIPELINES
$template = $template -replace '\{\{GITHUB_USER\}\}', $GITHUB_USER
$template | Set-Content "CLAUDE.md" -NoNewline

Ok "CLAUDE.md generated"

# ── Step 3: Platform-specific files ────────────────────────────
foreach ($platform in $PLATFORMS) {
    switch ($platform) {
        "claude" {
            Info "Setting up Claude Code..."
            New-Item -ItemType Directory -Force -Path ".claude\commands" | Out-Null
            New-Item -ItemType Directory -Force -Path ".claude\agents" | Out-Null
            $settingsTemplate = Get-Content "$SCRIPT_DIR\kernel\templates\settings.json.template" -Raw
            $settingsTemplate = $settingsTemplate -replace '\{\{AZOTH_VERSION\}\}', $AZOTH_VERSION
            $settingsTemplate | Set-Content ".claude\settings.json" -NoNewline
            Ok "Claude Code configured (.claude\)"
        }
        "opencode" {
            Info "Setting up OpenCode..."
            New-Item -ItemType Directory -Force -Path ".opencode\agent" | Out-Null
            New-Item -ItemType Directory -Force -Path ".opencode\command" | Out-Null
            $ocTemplate = Get-Content "$SCRIPT_DIR\kernel\templates\platform-adapters\opencode\opencode.jsonc.template" -Raw
            $ocTemplate = $ocTemplate -replace '\{\{MODEL\}\}', "claude-sonnet-4-20250514"
            $ocTemplate | Set-Content "opencode.jsonc" -NoNewline
            Ok "OpenCode configured (.opencode\, opencode.jsonc)"
        }
        "codex" {
            Info "Setting up Codex..."
            New-Item -ItemType Directory -Force -Path ".codex\agents" | Out-Null
            New-Item -ItemType Directory -Force -Path ".codex\hooks" | Out-Null
            Copy-Item "$SCRIPT_DIR\kernel\templates\platform-adapters\codex\config.toml.template" ".codex\config.toml"
            Copy-Item "$SCRIPT_DIR\kernel\templates\platform-adapters\codex\hooks.json.template" ".codex\hooks.json"
            Copy-Item "$SCRIPT_DIR\kernel\templates\platform-adapters\codex\user_prompt_submit_router.py.template" ".codex\hooks\user_prompt_submit_router.py"
            Ok "Codex configured (.codex\)"
        }
        "copilot" {
            Info "Setting up GitHub Copilot..."
            New-Item -ItemType Directory -Force -Path ".github\agents" | Out-Null
            New-Item -ItemType Directory -Force -Path ".github\prompts" | Out-Null
            $cpTemplate = Get-Content "$SCRIPT_DIR\kernel\templates\copilot-instructions.md.template" -Raw
            $cpTemplate = $cpTemplate -replace '\{\{PROJECT_NAME\}\}', $PROJECT_NAME
            $cpTemplate | Set-Content ".github\copilot-instructions.md" -NoNewline
            Ok "Copilot configured (.github\)"
        }
    }
}

# ── Step 4: Skills ─────────────────────────────────────────────
if ($INSTALL_SKILLS -and (Test-Path "$SCRIPT_DIR\skills")) {
    Info "Installing skills..."
    New-Item -ItemType Directory -Force -Path "skills" | Out-Null
    Copy-Item "$SCRIPT_DIR\skills\*" "skills\" -Recurse -ErrorAction SilentlyContinue
    if ($PLATFORMS -contains "codex") {
        New-Item -ItemType Directory -Force -Path ".agents\skills" | Out-Null
        Copy-Item "$SCRIPT_DIR\skills\*" ".agents\skills\" -Recurse -ErrorAction SilentlyContinue
    }
    Ok "Skills installed"
} elseif ($INSTALL_SKILLS) {
    Warn "Skills directory not found in Azoth source (Phase 2 not yet built)"
}

# ── Step 5: Agents ─────────────────────────────────────────────
if ($INSTALL_AGENTS -ne $false -and (Test-Path "$SCRIPT_DIR\agents")) {
    Info "Installing agents..."
    New-Item -ItemType Directory -Force -Path "agents" | Out-Null
    if ($INSTALL_AGENTS -eq "tier1") {
        Copy-Item "$SCRIPT_DIR\agents\tier1-core\*" "agents\" -Recurse -ErrorAction SilentlyContinue
    } else {
        Copy-Item "$SCRIPT_DIR\agents\*" "agents\" -Recurse -ErrorAction SilentlyContinue
    }
    Ok "Agents installed"
} elseif ($INSTALL_AGENTS -ne $false) {
    Warn "Agents directory not found in Azoth source (Phase 3 not yet built)"
}

# ── Step 6: Initialize memory ──────────────────────────────────
Info "Initializing memory system..."

if (-not (Test-Path ".azoth\memory\episodes.jsonl")) {
    New-Item -ItemType File -Force -Path ".azoth\memory\episodes.jsonl" | Out-Null
}

if (-not (Test-Path ".azoth\memory\patterns.yaml")) {
    @"
# Azoth Semantic Memory (M2)
# Promoted from M3 episodes via Promotion Rubric
patterns: []
"@ | Set-Content ".azoth\memory\patterns.yaml"
}

Copy-Item "$SCRIPT_DIR\kernel\templates\bootloader-state.md.template" ".azoth\bootloader-state.md" -ErrorAction SilentlyContinue

Ok "Memory system initialized"

# ── Step 7: Generate kernel checksums ──────────────────────────
Info "Generating kernel checksums..."
$checksums = Get-ChildItem ".azoth\kernel\*.md" | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
    "$hash  $($_.FullName)"
}
$checksums | Set-Content ".azoth\kernel-checksums.sha256"
Ok "Kernel integrity baseline established"

# ── Step 8: Gitignore runtime state ────────────────────────────
$gitignoreEntries = @(
    ""
    "# Azoth runtime state"
    ".azoth/telemetry/"
    ".azoth/session-orientation.txt"
    ".azoth/bootloader-state.md"
    ".azoth/kernel-checksums.sha256"
    ".azoth/proposals/"
)

if (Test-Path ".gitignore") {
    $content = Get-Content ".gitignore" -Raw
    if ($content -notmatch "\.azoth/telemetry") {
        $gitignoreEntries | Add-Content ".gitignore"
    }
    $content2 = Get-Content ".gitignore" -Raw
    if ($content2 -notmatch "\.azoth/proposals/") {
        Add-Content ".gitignore" ".azoth/proposals/"
    }
} else {
    $gitignoreEntries | Set-Content ".gitignore"
}

Ok "Gitignore updated"

# ── Step 9: Generate manifest ──────────────────────────────────
@"
name: azoth
version: $AZOTH_VERSION
project: $PROJECT_NAME
installed:
  kernel: true
  skills: $($INSTALL_SKILLS.ToString().ToLower())
  agents: $INSTALL_AGENTS
platforms: [$($PLATFORMS -join ', ')]
"@ | Set-Content "azoth.yaml"

Ok "Manifest generated (azoth.yaml)"

# ── Summary ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        🧪 AZOTH — Installation Complete         ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "║  Project: $PROJECT_NAME" -ForegroundColor Green
Write-Host "║  Kernel:  deployed to .azoth\kernel\             ║" -ForegroundColor Green
Write-Host "║  Memory:  initialized (.azoth\memory\)           ║" -ForegroundColor Green
Write-Host "║  Platforms: $($PLATFORMS -join ', ')" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "║  Next: Open your AI coding tool and start a      ║" -ForegroundColor Green
Write-Host "║  session. The agent will read CLAUDE.md and      ║" -ForegroundColor Green
Write-Host "║  boot automatically.                             ║" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
