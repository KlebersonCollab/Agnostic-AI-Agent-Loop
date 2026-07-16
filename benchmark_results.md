# Benchmark Results: Classic vs Orchestrator

**Model**: tencent/hy3:free (openrouter)

| Task | Mode | Success | Steps | Time | Tokens | Tools Used | Info |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| Task 1: File Read & Calculation | Classic | True | 3 | 9.51s | 30776 | write_file, read_file | Success (63) |
| Task 1: File Read & Calculation | Orchestrator | True | 2 | 17.01s | 17990 | spawn_subagents_parallel | Success (63) |
| Task 2: Code Bug Fixing & Validation | Classic | True | 4 | 10.47s | 41342 | execute_command, patch_file, read_file | Success (Correctly fixed and validated) |
| Task 2: Code Bug Fixing & Validation | Orchestrator | True | 2 | 22.50s | 18474 | spawn_subagents_parallel | Success (Correctly fixed and validated) |
| Task 3: Memory Database Query | Classic | True | 4 | 13.88s | 44118 | search_memory | Success (Found 2026-07-15) |
| Task 3: Memory Database Query | Orchestrator | True | 2 | 6.20s | 19544 | search_memory | Success (Found 2026-07-15) |