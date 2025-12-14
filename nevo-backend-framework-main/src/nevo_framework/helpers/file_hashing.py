import hashlib

import nevo_framework.helpers.file_tools as file_tools


def compute_fileset_hash(folder, extensions):
    files = sorted(list(file_tools.get_files_recursive(folder, extensions=extensions)))
    # Create a hash object
    hash_object = hashlib.sha256()
    for file_path in files:
        # Open the file in binary mode
        with open(file_path, "rb") as file:
            print(f"Computing hash for {file_path}")
            # Read the file in chunks to avoid loading the entire file into memory
            for chunk in iter(lambda: file.read(4096), b""):
                # Update the hash object with the chunk
                hash_object.update(chunk)

    # Get the hexadecimal representation of the hash value
    hash_value = hash_object.hexdigest()
    return hash_value


if __name__ == "__main__":
    folder = "."
    extensions = [".py"]
    hash_value = compute_fileset_hash(folder, extensions)
    print(f"Hash value for files in {folder}: {hash_value}")
