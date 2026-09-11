"""GMS — Gym Management System."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gms-app")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["__version__"]


def main() -> None:
    print("Hello from gms-app!")
