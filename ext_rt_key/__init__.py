from ext_rt_key import _version  # noqa: D104

__all__ = (
    "__appname__",
    "__version__",
)

__appname__ = "ext_rt_key"
__version__ = _version.get_versions()["version"]

from . import _version
__version__ = _version.get_versions()['version']
