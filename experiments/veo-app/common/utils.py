def print_keys(obj, prefix=""):
    """Recursively prints keys of a JSON object."""
    if isinstance(obj, dict):
        for key in obj:
            print(prefix + key)
            print_keys(obj[key], prefix + "  ")  # Recurse with increased indentation
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            print_keys(item, prefix + f"  [{i}] ")  # indicate list index in prefix

