import hashlib
from pathlib import Path


storage_path = Path.home() / ".app-simulator"


def save_file(filename, data):
    storage_path.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha1()
    hasher.update(data)
    sha = hasher.hexdigest()

    filename = f"{sha}{Path(filename).suffix}"

    path = storage_path.joinpath(filename)
    with open(path, "wb") as f:
        f.write(data)

    return filename


def get_file(filename):
    path = storage_path.joinpath(filename)
    if path.exists():
        return str(path)


def clean_storage():
    import shutil

    shutil.rmtree(storage_path, ignore_errors=True)
