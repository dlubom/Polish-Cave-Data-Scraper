---
name: cave-scraping
description: Change or diagnose CBDG cave and bibliography fetching in this repository, including HTTP sessions, anti-bot responses, pagination, and bounded smoke checks. Use for fetch.py or download_bibliography.py work, not offline parsing or archive restoration.
---

# CBDG fetching

Read the relevant script and [fetching behavior](../../../docs/pipeline.md#fetching). Determine
whether the task is a code fix, a bounded live check, or a requested dataset refresh. A code fix
normally needs mocked HTTP tests; it does not imply running the scraper against CBDG.

## Requests and failure handling

- Preserve one stable session and User-Agent, existing pacing, request timeouts, challenge
  detection before saving HTML, and JPEG validation. Treat HTTP 200 and parseable JSON as
  transport/format evidence, not proof that the content is the requested record.
- Distinguish HTTP errors, challenges, invalid payloads, empty results, and local permissions.
  Check termination for bibliography pages, especially jqGrid `total=0` and string page counts.
- Never replace a valid file with a known challenge or non-image body. Exercise preservation
  of existing files with mocked failures and temporary cave directories when changing downloads.

## Bounded live checks

When a live check is part of the task, create an isolated temporary working directory, keep the
repository path available for imports, and invoke the needed function or configure the imported
module's constants there. `fetch.py` has no CLI flags for ID ranges or output paths. Do not run
its default 380–13000 range as a smoke test. ID 395 is a historical example, not guaranteed access.

Check `tableDetails1`, expected metadata IDs, and a decodable JPEG in the temporary output.
Stop at the first anti-bot challenge and report the block without repeated retries or identity
rotation. For bibliography, bound the query/output and keep the output file outside tracked data.

Report whether validation used mocks or live responses, the actual IDs/pages checked, and what
was saved. Do not call a blocked/partial run a completed refresh.
