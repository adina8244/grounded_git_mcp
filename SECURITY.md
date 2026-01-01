# Security Policy

This document describes the security model, threat assumptions, and safety
guarantees of **grounded-git-mcp**.

The goal of this project is to provide AI agents with **safe, controlled,
local-only access to Git repositories**, without exposing users to accidental
or malicious repository modifications.

---

## Scope

- **Local MCP server only**
- Operates on a **local Git repository**
- **No network access required**
- **No GitHub API usage**
- **No shell execution**

This project is intentionally scoped to local environments to minimize
the attack surface and avoid remote side effects.

---

## Threat Model

The primary threats considered in this project are:

1. **Accidental destructive Git commands**
   - e.g. `reset --hard`, `clean -fd`, `push --force`
2. **Prompt-induced unsafe behavior**
   - AI agents generating unintended or dangerous commands
3. **Hung or long-running Git processes**
   - e.g. credential helpers, pagers, or SSH subprocesses
4. **Unbounded output or resource usage**
   - very large diffs, logs, or file contents
5. **OS-specific process handling risks**
   - differences between Windows and POSIX process models

---

## Security Guarantees & Mitigations

### Read-Only by Default

- All Git commands are executed in **read-only mode by default**
- Only an explicit allowlist of safe subcommands is permitted
- Any potentially mutating command is **blocked unless explicitly allowed**

### Explicit Write Opt-In

- Write operations require:
  - `read_only=False`
  - An explicit caller decision
- This prevents silent or implicit repository mutation by AI agents

### No Shell Execution

- Commands are executed using `subprocess.Popen` with `shell=False`
- Arguments are passed as lists, eliminating shell injection risks

### Strict Root Enforcement

- All Git commands are executed **only inside a validated repository root**
- Path traversal or execution outside the repository is not permitted

### Hard Timeouts & Process Cleanup

- All Git commands are executed with **hard timeouts**
- Stuck or hung processes are forcefully terminated:
  - POSIX: process group termination
  - Windows: full process tree termination
- This prevents resource exhaustion and orphaned processes

### Controlled Execution Environment

- Interactive Git behavior is disabled:
  - No terminal prompts
  - No credential managers
  - No pagers
- Environment variables are sanitized and explicitly set

### Output Size Limiting

- Combined stdout/stderr output is capped
- Deterministic truncation is applied
- Prevents memory pressure and excessive token usage by AI agents

---

## Platform Considerations

- The project explicitly supports **Windows and POSIX platforms**
- OS-specific process termination logic is implemented and tested
- Platform-dependent behavior is isolated and covered by unit tests

---

## Vulnerability Reporting

If you discover a security vulnerability or unsafe behavior:

- Please open a **GitHub Issue** with the label `security`
- Do **not** publish exploit details publicly before discussion

Responsible disclosure is appreciated.

---

## Design Philosophy

Security in this project is **enforced by code**, not by prompts or conventions.

AI agents are treated as:
> powerful but fallible automation tools

Accordingly, all safety guarantees are implemented at the execution layer,
not delegated to model behavior.

---

## Summary

This project intentionally prioritizes:

- Explicitness over convenience
- Safety over automation
- Deterministic behavior over heuristics

These design choices ensure that grounded-git-mcp can be safely used as a
foundation for AI-assisted Git analysis and debugging workflows.
