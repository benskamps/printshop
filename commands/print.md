---
description: Make something to print — a fitted one-page guide, sheet, form or card — and offer to send it to the printer
argument-hint: [what to print, e.g. "a one-page cheat sheet for emberctl"]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Use the **printshop** skill (`~/projects/printshop/skills/printshop/SKILL.md`) to
build a printable document for: **$ARGUMENTS**

Follow its workflow exactly:

1. Read the skill file first if it is not already loaded.
2. Write the source markdown to `~/cockpit/print/` (create it if needed) with
   front matter — pick the theme, paper and `fit:` target that suit the job.
   Default to `fit: 1` unless the content genuinely cannot carry it.
3. `render`, then `preview`, then **Read the preview PNG** and judge it. Fix
   what the solver cannot see: stranded headings, bad table wraps, a column
   break through a callout.
4. Report the fit summary (page count, scale, columns) to the user, then **ask
   before sending it to the printer**. Do not print unattended.
