# Claude Context Management Guide

Goal: a session can be restarted or compacted cheaply, because state lives in the repo (`CLAUDE.md`, `.claude/progress.md`, Git, tests), not in conversation history.

## Starting a New Session

1. Read `CLAUDE.md`.
2. Read `.claude/progress.md`.
3. Run `git status` (and `git log -3 --oneline`).
4. Inspect only the files relevant to the current objective.
5. Verify `progress.md` against the actual repository state.
6. If documentation and code conflict, the code/Git state wins; then fix the doc.

Startup prompt:

```
Read CLAUDE.md and .claude/progress.md first.
Inspect the current Git status and relevant implementation files.
Verify the documented state against the repository.
The repository is the source of truth.
Then continue from the documented next action.
Do not perform a repository-wide scan unless necessary.
```

## During Development

- Use targeted searches (`grep` a symbol, `ls` one directory) instead of reading whole trees.
- Do not re-read unchanged large files; read line ranges.
- Send long command output to a file (scratchpad) and read only the tail or a grep.
- Do not open generated/data files (see the "Avoid" list in `CLAUDE.md`).
- Run targeted tests first; the full backend suite takes over 10 minutes.
- Update `progress.md` only at meaningful milestones (phase finished, decision made, handing off), not after every step.
- Keep `progress.md` a current-state snapshot: delete finished/obsolete items rather than appending history. Target well under 150 lines.

## Before Compaction

Use this prompt:

```
We are preparing to compact this Claude Code session.

Review what was actually completed.

Update .claude/progress.md with only the information necessary for another session to continue:
- current objective
- completed work
- files changed
- important decisions
- tests and results
- unresolved issues
- remaining work
- exact next action

Remove obsolete information.
Do not copy conversation history, huge logs, diffs, or full file contents.
Do not modify application code during this checkpoint.
The repository remains the source of truth.
```

After Claude updates the file, run `/compact`.

## Starting Fresh Instead of Carrying Huge Context

When a session has accumulated a very large context, a clean session is usually better once `progress.md` is up to date. The new session rebuilds state from `CLAUDE.md` + `.claude/progress.md` + Git + the relevant source files + tests, instead of paying to re-process hundreds of thousands of tokens of old conversation. Use the startup prompt above.
