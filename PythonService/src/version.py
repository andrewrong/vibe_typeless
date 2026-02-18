"""
Typeless Python Service Version Information
"""

__version__ = "0.3.0"
__build__ = "20250218"
__commit__ = "03612b5"


def get_version_info() -> dict:
    """Get full version information"""
    return {
        "version": __version__,
        "build": __build__,
        "commit": __commit__,
        "service": "typeless-python",
    }


def get_version_string() -> str:
    """Get version as string"""
    return f"{__version__}+{__build__} ({__commit__})"
