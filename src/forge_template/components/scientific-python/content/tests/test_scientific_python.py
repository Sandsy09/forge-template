"""Smoke tests for the Scientific Python capability."""

import matplotlib
import numpy
import pandas
import sklearn


def test_scientific_python_stack_is_importable() -> None:
    """Every package in the capability's public import surface is available."""
    versions = (
        matplotlib.__version__,
        numpy.__version__,
        pandas.__version__,
        sklearn.__version__,
    )

    assert all(isinstance(version, str) and version for version in versions)
