class DataBarnError(Exception):
    """Base class for all exceptions raised by DataBarn."""
    pass

class CobConsistencyError(DataBarnError):
    """Raised when an operation would lead to an inconsistent state in the Cob.
    This is a generic class for uncategorized Cob consistency error."""
    pass

class StaticModelViolationError(CobConsistencyError, SyntaxError):
    """Raised when a dynamic operation is attempted on a static model."""
    pass

class ConstraintViolationError(CobConsistencyError, ValueError):
    """Raised when an assignment to a grain fails due to constraint violations."""
    pass

class GrainTypeMismatchError(ConstraintViolationError, TypeError):
    """Raised when an assignment to a grain is of the wrong type."""
    pass

class InvalidGrainLabelError(DataBarnError, NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass

class BarnConsistencyError(DataBarnError, SyntaxError):
    """Raised when an operation would lead to an inconsistent state in the Barn."""
    pass