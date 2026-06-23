class CelestrakError(Exception):
    """Base de errores del driver de CelesTrak."""


class TleNotFound(CelestrakError):
    """404 / 'No GP data found': el CATNR o el grupo no existen."""


class RateLimitedError(CelestrakError):
    """403 de CelesTrak: refresco antes de las 2h o IP bloqueada.

    No reintentar en bucle: parar y avisar a un humano (CelesTrak banea IPs
    que superan el umbral de errores).
    """


class TransientError(CelestrakError):
    """Timeout, error de red o 5xx. El job puede reintentar con backoff."""
