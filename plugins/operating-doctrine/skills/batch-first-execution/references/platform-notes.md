# Platform behavior and source notes

Verified against public provider documentation on 2026-09-23. Recheck live
documentation before recommending settings or shortcuts on later dates.
This file records provider behavior, not the installed versions or settings
on Allison's devices. Source links are evidence, not permission grants.

## Codex: queue versus steer

OpenAI distinguishes Queue (send on the next run) from Steer (add guidance to
the current run). Its current prompting page documents desktop follow-up
settings and CLI keys. Verify the exact surface before applying these details.

For ordered subsequent tasks, use Queue. Use Steer deliberately for a current
correction. Neither label proves that task-specific acceptance checks passed.

Primary sources:
- https://learn.chatgpt.com/docs/prompting
- https://developers.openai.com/blog/mastering-codex-remote-for-engineering

## Claude Code: queued text is not necessarily after the whole task

Anthropic's interactive-mode page documents Enter to queue while Claude
works. It also says ordinary messages queued during tool calls can reach Claude
when those calls finish, within the same turn. Commands and shell commands
have different delivery behavior. Do not describe all queued text as a strict
end-of-task FIFO, and do not transfer terminal behavior to Desktop or an IDE.

Keep one ordered mission in the checkpoint for coherent dependent work.
For a Claude Code paste governed by `code-block-routing`, deliver only the
first step in one block per response; verify its result before the next block.
When separate messages are requested on a permitted surface, repeat dependency
guards in every block. Test an unfamiliar surface with a harmless bounded
fixture before real writes; do not change permissions or install software just
to test its input behavior.

Primary source:
- https://code.claude.com/docs/en/interactive-mode#queue-messages-while-claude-works

## Plans, verification and recovery

OpenAI's ExecPlan guidance uses self-contained evolving plans and verifiable
milestones. Anthropic's best-practice guidance emphasizes checks the worker
can run and inspect. Apply these concepts without reproducing their templates
or treating an experimental long run as a reliability guarantee.

Primary sources:
- https://developers.openai.com/cookbook/articles/codex_exec_plans
- https://code.claude.com/docs/en/best-practices

## Skill portability is not universal activation

Claude Code follows the Agent Skills open standard. Codex documents local
skill discovery and plugin distribution. Package common Markdown instructions
with conservative name/description frontmatter; keep app-specific behavior in
this reference rather than pretending all clients have identical controls.

A compatible bundle is not automatically installed, enabled, discovered or
behaviorally reliable. ChatGPT, Claude chat, Claude Code and Codex each require
an actual supported installation/discovery path. For another assistant without
verified skill support, supply a clearly labeled instruction-file adaptation,
not a claim of native skill installation.

Primary sources:
- https://code.claude.com/docs/en/skills
- https://learn.chatgpt.com/docs/build-skills

## Unknown local behavior

Where the owning routing rule permits it, use the master-assignment format
rather than guessing a shortcut. For Claude Code, follow the step-one-only
rule above. Distinguish three statements: "provider documents this," "this
device has this version," and "we tested this behavior here." Never
substitute one for another.
