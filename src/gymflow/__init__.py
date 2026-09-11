"""GymFlow — Sistema de gerenciamento para academias com Henry 7x."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gymflow")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["__version__"]


def main() -> None:
    print("Hello from gymflow!")
