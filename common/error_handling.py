class GenerationError(Exception):
    """Custom exception for video generation errors."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
