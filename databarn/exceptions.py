"""Custom exception hierarchy for DataBarn."""

class DataBarnViolationError(Exception):
    """Base class for all exceptions raised by DataBarn."""
    pass

class ValidationError(DataBarnViolationError, ValueError):
    """Raised when validation of input or data fails within DataBarn."""
    pass

class DataBarnSyntaxError(DataBarnViolationError, SyntaxError):
    """Raised when an operation violates the syntax rules of DataBarn."""
    pass

class SchemaViolationError(DataBarnViolationError):
    """Raised when an operation violates the schema constraints,
      or would lead to an inconsistent state in the Cob or Barn."""
    pass

class GrainTypeMismatchError(SchemaViolationError, TypeError):
    """Raised when an assignment to a grain is of the wrong type."""
    pass

class GrainLabelError(DataBarnViolationError, NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass
