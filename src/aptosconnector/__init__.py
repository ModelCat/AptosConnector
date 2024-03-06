from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aptosconnector")
except PackageNotFoundError:
    __version__ = "dev"
