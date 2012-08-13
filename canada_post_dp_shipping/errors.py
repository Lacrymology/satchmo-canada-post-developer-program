class ParcelDimensionError(Exception):
    """
    Exception raised when the parcel created is too large for Canada Post
    shipping. This can be activated and deactivated from livesettings
    """