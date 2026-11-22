# Executed workflow scenarios

These are local acceptance scenarios with deterministic outputs—not a claim that a model runtime executed the Markdown skills.

| Scenario | Skill contract used | Operation under test | Expected | Result |
|---|---|---|---|---|
| User describes work in chat | `create-task`: classify as `source.type: ui`, let CLI allocate the next number and register it, do not scan task directories or ask the user, do not invent | `arch task new --title "..."` | Task created and registered as `UI-NNNN` | Automated test passed |
| Jira work item | `create-task`: preserve Jira source, no key prefix | `arch task-key --source jira --number 0427` | `0427` | Automated test passed |
| Other provider | `create-task`: require configured source prefix | `arch task-key --source github --prefix gh --number 0042` | `GH-0042` | Automated test passed |
| Invalid number / disallowed prefix | Intake must fail closed | CLI cases: 3/5 digits, alphabetic digit, Jira prefix, non-UI prefix on UI, UI prefix on another provider | Nonzero exit | Automated tests passed |
| Resume numbered task | `go-to-task`: exact key, validate source/number form, inspect task/stage | Load `doc/tasks/UI-0001/task.json` and compare `task_number`, `task_key`, source and directory | Consistent UI task fixture | Automated test passed |
| Registry drift after manual card | Maintenance: registry is CLI-owned; drift is detected, not ignored | Create a card without registry entry, then run `arch task registry check` and `arch task registry sync` | Check exits 1 without writing; sync adds the entry from `task.json` | Automated tests passed |
| Document the current task | `задокументируй`: report only actual facts; preserve task/evidence | Inspect task plan and verification JSON; run architecture validation | Numbered task, reproducible checks, no false pass claim | Automated checks passed |
| Dirty shared tree before writing | `go-to-task`: isolate when another writer touched declared files | `arch task workspace UI-9999 --json` with a changed declared path | `preflight.status: isolate` and the path in `intersections` | Automated test passed |
| Historical closure after the tree changed | `go-to-task`: separate closure from current freshness | `arch task diagnose UI-9999 --json` and `arch task evidence UI-9999 --check` | `evidence_freshness.status: stale`, `note`, and `--check` exit 1 with `stale_files` | Automated test passed |
| Record a pre-change baseline | `go-to-task`: keep the starting result for comparison | `arch task baseline UI-9999 --file input.txt --run ...` | `stage1/baseline.json` with command, exit code and hashes; changed input is refused | Automated test passed |
| Targeted iteration | Test runner contract: select a group without a full gate | `bash doc/tests/run.sh --only plan_tier` | Selected tests run; an empty selector exits 1 | Manual run passed |

The last two rows validate the artifact/contract and checks, not an actual LLM following a skill. A product-code task cannot be run here: no product repository, authorized task number/source allocation, acceptance oracle, CI and sandbox are configured.
