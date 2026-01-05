from pathlib import Path

def scan_directory(path: str | Path) -> str:
    """
    Recursively scans a directory and returns a formatted tree structure of files.
    Skips hidden files and __pycache__.
    """
    path = Path(path)
    if not path.exists():
        return f"Error: Path '{path}' not found."

    output = []
    output.append(f"Directory listing for: {path.absolute()}")

    # Simple recursive walk
    for item in sorted(path.rglob("*")):
        # Skip hidden files and pycache
        if any(part.startswith(".") for part in item.parts) or "__pycache__" in item.parts:
            continue

        relative_path = item.relative_to(path)
        type_label = "[DIR] " if item.is_dir() else "[FILE]"
        output.append(f"{type_label} {relative_path}")

    return "\n".join(output)
