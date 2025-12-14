import hashlib
import os
from typing import Generator, List


def preview_text(string: str, max_length: int = 300) -> str:
    """
    Shorten a string if it is longer than `max_length` characters and simplify it for display.
    The shortened string will have the first `max_length - 3` characters followed by "...".
    """
    preview = string.replace("\n", " ")
    if len(preview) > max_length:
        return preview[: max_length - 3] + " [...]"
    else:
        return preview


def is_subpath(path, subpath):
    """Check if subpath is a subpath of path."""
    # Get the absolute, normalized path of p1 and p2
    abs_p1 = os.path.abspath(os.path.normpath(path))
    abs_p2 = os.path.abspath(os.path.normpath(subpath))

    # Check if p1 starts with p2
    return abs_p2.startswith(abs_p1)


def get_files_recursive(directory: str, extensions: str | List[str] | None) -> Generator:
    """
    Generator to get all files in the directory and its subdirectories.
    Yields the full path of each file.

    Parameters:
    - `directory` is the directory to search.
    - `extensions` limits the files to those with the specified extensions. It can be a string for a single extension
        or a list of strings for multiple extensions. If None, all files are returned.
    """
    if isinstance(extensions, str):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if extensions and file.endswith(extensions):
                    yield os.path.join(root, file)
    elif isinstance(extensions, list):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    yield os.path.join(root, file)
    else:
        raise ValueError("extensions must be a string or a list of strings.")


def compute_fileset_hash(folder: str, extensions: str | List[str] | None) -> str:
    """
    Compute a hash value of all files in `folder` and its subdirectories, possibly filtered by `extensions`
    which can be a string for a single extension or a list of strings for multiple extensions.
    This value changes if the content of any file in the folder changes or if a file is added or removed.
    """
    files = sorted(list(get_files_recursive(folder, extensions=extensions)))
    # Create a hash object
    hash_object = hashlib.sha256()
    for file_path in files:
        # include the file path in the hash value to detect name changes without content changes
        hash_object.update(file_path.encode())
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_object.update(chunk)

    # Get the hexadecimal representation of the hash value
    hash_value = hash_object.hexdigest()
    return hash_value


if __name__ == "__main__":
    folder = "."
    extensions = [".py"]
    hash_value = compute_fileset_hash(folder, extensions)
    print(hash_value)
