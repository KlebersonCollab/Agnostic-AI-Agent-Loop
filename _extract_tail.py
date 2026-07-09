with open("cli.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Write lines from index 119 (line 120) onward to a separate file
with open("_cli_tail.txt", "w", encoding="utf-8") as out:
    out.writelines(lines[119:])
