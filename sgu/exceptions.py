class StartTimeNotFoundError(Exception):
    """When the start time of a segment cannot be found."""

    def __init__(self, message: str):
        super().__init__(message)
