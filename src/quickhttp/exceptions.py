class QuickhttpException(Exception):
    """Base exception for all quickhttp custom exceptions."""


class InvalidPortRangeError(QuickhttpException, ValueError):
    pass
