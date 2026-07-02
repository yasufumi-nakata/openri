"""Open Research Integrity test runner."""

__version__ = "0.4.0"
__homepage__ = "https://github.com/yasufumi-nakata/openri"

from .analyzer import analyze_manuscript

__all__ = ["analyze_manuscript", "__homepage__", "__version__"]
