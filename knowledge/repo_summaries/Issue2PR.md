Purpose:
The purpose of the Issue2PR repository is to create an agentic AI contributor for open-source Go projects, which can take a GitHub issue, inspect the repository, locate the relevant code, write a plan, apply a fix, validate it, and produce a PR title and body.

Tech stack:
The tech stack used in this repository includes Python 3.10+, the Go toolchain (go, gofmt), git, and various LLM backends such as OpenRouter, Groq, and Gemini.

Architecture:
The architecture of the Issue2PR system is a hybrid system, consisting of a deterministic outer pipeline wrapping an agentic inner tool-loop. The pipeline consists of several stages, including fetch issue, prepare repo, analyze, apply fix, validate, PR summary, and artifacts.

Design tradeoffs:
The design tradeoffs made in this system include using a hybrid approach, where the deterministic shell is reliable and reproducible, and the LLM is used only where judgement is needed. Another tradeoff is the use of anchored edit_file over patches, as free/open models reliably produce exact-snippet replacements but frequently emit malformed unified diffs.

What she'd do differently / future work:
Not documented