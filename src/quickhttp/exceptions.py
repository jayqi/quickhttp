class QuickhttpException(Exception):
    """Base exception for all quickhttp custom exceptions."""


class NoAvailablePortFoundError(QuickhttpException):
    pass


class InvalidSearchTypeError(QuickhttpException, ValueError):
    pass
