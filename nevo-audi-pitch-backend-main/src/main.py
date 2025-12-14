from pathlib import Path
import sys

from dotenv import load_dotenv


def _ensure_framework_on_path() -> None:
    """
    Allow running the backend when the framework repo lives next to this repo.

    If `nevo_framework` is already installed (e.g. via `pipenv install -e ../nevo-backend-framework-main`)
    the import below will just work. When someone downloaded the repos as ZIP files and has not installed
    the framework package, this helper will append the sibling framework directory to `sys.path` so that
    `import nevo_framework` still succeeds.
    """

    framework_dir = (
        Path(__file__)
        .resolve()
        .parents[2]  # workspace root (go up from src/main.py -> repo root -> workspace root)
        / "nevo-backend-framework-main"
        / "src"
    )
    if framework_dir.exists() and str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))


_ensure_framework_on_path()
load_dotenv()  # the order is important here: load_dotenv MUST be called before framework import

from nevo_framework.api import api as framework_api

if __name__ == "__main__":
    framework_api.main()
