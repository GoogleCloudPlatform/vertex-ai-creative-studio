---title: "Agent Aware Cli"

name: agent-aware-cli
description: Guide for designing and implementing command-line interfaces (CLIs) that are equally usable by human developers and automated coding agents. Use when the user wants to build a CLI, apply CLI best practices, or use Go with Cobra and Viper.
---

When tasked with building or improving a Command Line Interface (CLI), follow these architectural and design best practices to ensure it serves both human operators (with rich TUIs) and AI agents (with deterministic, machine-readable output).

## Core Principles

1. **The Dual-Experience Paradigm (DX & AX)**
   This CLI must be designed as a "Dual-Mode" interface, treating both humans and AI agents as first-class users.
   - **DX (Developer Experience)**: Ergonomics for human operators. Emphasizes discoverability, rich TUIs (e.g., Bubbletea, Lipgloss), semantic coloring, and intuitive aliases.
   - **AX (Agent Experience)**: Ergonomics for autonomous AI agents. Emphasizes determinism, strict machine-readable output modes (e.g., `--json`), headless authentication, aggressive data scoping (limits/filtering), and mutative safety (`--dry-run`).
   - **Environment Overrides**: Respect `NO_COLOR` and `[APP]_NO_TUI` environment variables to automatically fall back to non-interactive, unstyled modes.

2. **Headless-Friendly Authentication**
   - Agents cannot complete interactive, browser-based OAuth flows. CLIs must either support headless auth methods (Service Accounts, API Keys via ENV vars, `--token` flags) OR immediately fail with a clear, machine-readable error instructing the human operator to authenticate manually first.

3. **Sane Defaults & Aggressive Filtering**
   - Never dump unpaginated or unfiltered lists to `stdout`. Default to sensible limits (e.g., top 10 items). Provide rich filtering flags (e.g., `--status`, `--mine`, `--limit`) so agents can surgically query exactly what they need without blowing out their token context.

4. **Mutative Safety (`--dry-run`)**
   - For commands that create, update, or delete external state, implement a `--dry-run` flag. This allows an autonomous agent to test its parameter mapping and validate the resulting payload locally before executing the destructive action.

5. **Context Window Protection**
   - Agents have limited context windows. Actively truncate massive text blobs, sort critical action items to the top, and mask raw credentials by default to prevent credential leakage.
   - Provide opt-in verbosity (e.g., `--full` or `--verbose`) for agents or humans who explicitly request unfiltered data.

6. **Executable Proactive Error Hints**
   - Don't just report failures; provide the exact steps to fix them.
   - Inject copy-pasteable terminal commands into `stderr` (e.g., `Hint: run 'app init' to create a database`). This enables autonomous agents to parse the error and self-correct seamlessly.

7. **Delegated State Management**
   - Avoid maintaining long-running state loops within the CLI if orchestrating complex workflows.
   - Use a stateless task identifier pattern (`--task <ID>`, `--ref <ID>`). Pass the ID back to the backend service, which maintains the token context window and conversation history.

8. **Externalized Agent Instructions**
   - Add an `AGENTS.md` or `GEMINI.md` file at the repository root explaining the tool's usage, workflows, and standards for AI developers.
   - Provide an `agentskills.io` compliant `skills/` directory with `SKILL.md` files for complex subcommands.

9. **API Discovery & Progressive Convenience**
   - When building a CLI against a large Google/REST API, analyze its **Discovery Document** (e.g. `https://youtube.googleapis.com/$discovery/rest?version=v3`) to understand the exact, strict mappings of resources, methods, query parameters, and required OAuth scopes.
   - Consider auto-generating the base commands directly from the Discovery Document to guarantee 100% API coverage. 
   - **However, raw REST mappings are often un-ergonomic for humans**. You must layer "Convenience Wrappers" or "Hints" on top of the raw generated commands. For example, if a user asks to "list videos for a user", the CLI should intelligently abstract away the fact that it takes two API calls (one to resolve the handle to a Channel ID, and another to fetch the playlist) under a single `channel videos @user` command.

## Implementation with Go (Cobra & Viper)

When implementing a CLI in Go, use **Cobra** for command routing and **Viper** for configuration management.

### Cobra Practices
- **Structured Discoverability**: Prevent a "wall of text" in the root help output by using Cobra's `GroupID` to categorize commands (e.g., `Task Management`, `Information`).
- **The Three Pillars of Documentation**: Populate these fields for *every* command:
  - `Short`: A 5-10 word summary starting with an action verb for quick scanning.
  - `Long`: Detailed explanation of *what* it does, *why*, and its differentiation.
  - `Example`: 3-5 concrete, copy-pasteable examples showing common flag combinations.
- **Fail Fast Hooks**: Validate configuration and connectivity in `PersistentPreRun` hooks before executing heavy logic.

### Viper & Configuration Practices
- **XDG Compliance**: Follow the XDG Base Directory Specification for configuration files (e.g., `~/.config/app/config.yaml`).
- **Smart Fallbacks Priority**: Use Viper to ensure values resolve in this consistent order:
  `Command Line Flag > Environment Variable > Config File > Default Value`
- **Secrets Management**: Never allow API keys to leak into shell history. Prefer environment variables over CLI flags for secrets.

## Visual Information Design (Human Mode)

When optimizing the CLI for human readability, draw on Tufte-inspired principles to minimize cognitive load:
- **Maximize Data-Ink Ratio**: Minimize non-essential "ink" like decorative borders. Use whitespace and positioning as the primary tools for conveying hierarchy.
- **Resilient UI Formatting**: Always apply padding and width enforcement to raw strings *before* applying terminal styling (e.g., with `lipgloss`). Invisible ANSI escape codes can otherwise corrupt `fmt.Printf` table alignments.
- **The ANSI Alignment Gotcha**: When building TUI tables in Go, native tools like `text/tabwriter` or `fmt.Printf` will break alignment if you pass strings containing invisible ANSI color codes. You MUST pad strings to their fixed widths *before* applying color wrappers, or use a robust layout engine like `lipgloss.Table`.
- **Semantic Color Tokens**: Use specific functional colors rather than aesthetic ones:
  - `Accent` (Blue): Navigation landmarks, headers, group titles.
  - `Command` (Grey/Light Grey): Scan targets like command names and flags.
  - `Pass` (Green): Success states and completed tasks.
  - `Warn` (Orange/Yellow): Transient or pending states, warnings.
  - `Fail` (Red): Errors and rejected states.
  - `Muted` (Dark Grey): De-emphasis for metadata, types, or defaults.
  - `ID` (Teal/Mint): Unique identifiers.
- **Color Degradation**: Ensure colors degrade gracefully when piped to a file, when `--json` is invoked, or when `NO_COLOR` is present.

## Mandatory Implementation Checklist for Agents

When generating or updating a CLI command, you MUST ensure all of the following are implemented on your **first pass**. Do not treat UI/UX as an afterthought:

- [ ] **Dual-Experience (DX/AX)**: Does the command support a `--json` flag or respect `NO_COLOR`/`[APP]_NO_TUI`?
- [ ] **Headless Auth**: Can an agent run this command autonomously without hanging on a browser-based OAuth prompt?
- [ ] **Data Scoping**: If returning a list, are there sane default limits and filtering flags (e.g., `--limit`, `--status`)?
- [ ] **Mutative Safety**: If the command mutates state, does it include a `--dry-run` flag for agent safety?
- [ ] **Error Hints**: Do errors print actionable, copy-pasteable terminal commands to `stderr`?
- [ ] **XDG Compliance**: Is configuration handled via the XDG Base Directory specification (e.g. `~/.config/app/config.yaml`) instead of local `.env` files?
- [ ] **The Three Pillars**: Are `Short`, `Long`, and `Example` fields fully populated in the Cobra command definition?
- [ ] **Discoverability**: Is the command assigned to a logical `GroupID`?
- [ ] **Semantic Colors**: Is the human-readable output formatted using the semantic color tokens (e.g., Lipgloss)?
- [ ] **Alignment Safety**: If using raw ANSI colors in tables, is string padding applied *before* the color codes to prevent alignment breaking?
- [ ] **Help Formatting**: Have you overridden Cobra's default `SetUsageTemplate` to apply semantic colors to the help output itself (e.g., coloring headers blue)?
