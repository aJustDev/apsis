from app.core.celestrak.driver import CelestrakClient
from app.core.config import settings


class _CelestrakClientRegistry:
    """Singleton del cliente de CelesTrak.

    - Produccion: la primera llamada a `get()` construye el cliente HTTP
      desde settings.
    - Tests: `register(FakeCelestrakClient())` antes de ejecutar el codigo
      que lo consume, o `reset()` entre tests.
    """

    def __init__(self) -> None:
        self._client: CelestrakClient | None = None

    def register(self, client: CelestrakClient) -> None:
        self._client = client

    def get(self) -> CelestrakClient:
        if self._client is None:
            self._client = self._build_default()
        return self._client

    def reset(self) -> None:
        self._client = None

    def _build_default(self) -> CelestrakClient:
        from app.core.celestrak.drivers.http import CelestrakHttpClient

        return CelestrakHttpClient(
            base_url=settings.CELESTRAK_BASE_URL,
            timeout_seconds=settings.CELESTRAK_TIMEOUT_SECONDS,
        )


celestrak_client_registry = _CelestrakClientRegistry()
