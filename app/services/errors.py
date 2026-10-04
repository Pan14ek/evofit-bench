"""Expected business errors mapped to stable HTTP responses."""


class BusinessError(Exception):
    """Base class for expected business-rule failures."""


class NotFoundError(BusinessError):
    """A referenced entity does not exist."""


class ConflictError(BusinessError):
    """A unique or lifecycle conflict occurred."""


class InvalidRequestError(BusinessError):
    """A business request is invalid."""
