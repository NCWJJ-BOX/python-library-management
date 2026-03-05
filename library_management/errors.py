class LibraryError(Exception):
    pass


class ValidationError(LibraryError):
    pass


class NotFoundError(LibraryError):
    pass


class ConflictError(LibraryError):
    pass
