class ApplicationError(Exception):
    """Error de regla de negocio. Mensaje apto para mostrar al usuario."""

    def __init__(self, message: str, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
