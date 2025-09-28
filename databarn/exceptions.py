class DataBarnViolationError(Exception):
    """Base class for all exceptions raised by DataBarn."""
    pass

class DataBarnSyntaxError(DataBarnViolationError, SyntaxError):
    """Raised when an operation violates the syntax rules of DataBarn."""
    pass

class CobConsistencyError(DataBarnViolationError):
    """Raised when an operation would lead to an inconsistent state in the Cob.
    This is a generic class for uncategorized Cob consistency errors."""
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

class InvalidGrainLabelError(DataBarnViolationError, NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass

class BarnConsistencyError(DataBarnViolationError, ValueError, TypeError):
    """Raised when an operation would lead to an inconsistent state in the Barn."""
    pass
