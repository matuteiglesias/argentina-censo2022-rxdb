"""Argentina Census 2022 adapter contracts."""

from .sources import CensusSources, SourceDatabase, discover_sources

__all__ = ["CensusSources", "SourceDatabase", "discover_sources"]
__version__ = "0.0.1"
