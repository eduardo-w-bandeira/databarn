"""Custom exception hierarchy for DataBarn."""

class DataBarnViolationError(Exception):
    """Base class for all exceptions raised by DataBarn."""
    pass

class DataBarnSyntaxError(DataBarnViolationError, SyntaxError):
    """Raised when an operation violates the syntax rules of DataBarn."""
    pass

class SchemaValidationError(DataBarnViolationError):
    """Raised when an operation violates the schema constraints,
      or would lead to an inconsistent state in the Cob or Barn."""
    pass

class DataValidationError(SchemaValidationError, TypeError):
    """Raised when validation of input or data fails type or other constraints."""
    pass

class LabelValidationError(DataBarnViolationError, NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass
