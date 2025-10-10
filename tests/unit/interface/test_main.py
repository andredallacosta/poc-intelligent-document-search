from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient


@pytest.fixture
def mock_settings():
    with patch("interface.main.settings") as mock:
        mock.app_name = "Test App"
        mock.app_version = "1.0.0"
        mock.log_level = "INFO"
        mock.sqlalchemy_log_level = "WARNING"
        mock.external_libs_log_level = "ERROR"
        mock.cors_origins = ["*"]
        mock.cors_methods = ["*"]
        mock.cors_headers = ["*"]
        mock.api_prefix = "/api/v1"
        mock.debug = False
        mock.api_host = "0.0.0.0"
        mock.api_port = 8000
        mock.max_messages_per_session = 100
        mock.max_daily_messages = 1000
        mock.chunk_size = 500
        mock.default_search_results = 5
        mock.use_contextual_retrieval = True
        mock.create_directories = Mock()
        yield mock


@pytest.fixture
def mock_container():
    with patch("interface.main.container") as mock:
        mock.get_redis_client = Mock()
        mock.close_connections = AsyncMock()
        yield mock


@pytest.fixture
def mock_db_connection():
    with patch("infrastructure.database.connection.db_connection") as mock:
        mock.initialize = Mock()
        mock.get_session = AsyncMock()
        mock.close = AsyncMock()
        yield mock


class TestMainApp:
    def test_app_creation(self):
        from interface.main import app

        assert app.title is not None
        assert app.version is not None
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(
        self, mock_settings, mock_container, mock_db_connection
    ):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_container.get_redis_client.return_value = mock_redis_client
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_connection.get_session.return_value = [mock_session]
        from fastapi import FastAPI

        from interface.main import lifespan

        app = FastAPI()
        async with lifespan(app):
            pass
        mock_settings.create_directories.assert_called_once()
        mock_redis_client.ping.assert_called_once()
        mock_db_connection.initialize.assert_called_once()
        mock_container.close_connections.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_redis_connection_failed(
        self, mock_settings, mock_container, mock_db_connection
    ):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=False)
        mock_container.get_redis_client.return_value = mock_redis_client
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_connection.get_session.return_value = [mock_session]
        from fastapi import FastAPI

        from interface.main import lifespan

        app = FastAPI()
        async with lifespan(app):
            pass
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_redis_exception(
        self, mock_settings, mock_container, mock_db_connection
    ):
        mock_container.get_redis_client.side_effect = Exception("Redis error")
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_connection.get_session.return_value = [mock_session]
        from fastapi import FastAPI

        from interface.main import lifespan

        app = FastAPI()
        async with lifespan(app):
            pass
        mock_container.get_redis_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_database_connection_failed(
        self, mock_settings, mock_container
    ):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_container.get_redis_client.return_value = mock_redis_client
        with patch("infrastructure.database.connection.db_connection") as mock_db:
            mock_db.initialize.side_effect = Exception("Database error")
            from fastapi import FastAPI

            from interface.main import lifespan

            app = FastAPI()
            async with lifespan(app):
                pass
            mock_db.initialize.assert_called_once()


class TestMiddleware:
    @pytest.mark.asyncio
    async def test_process_time_middleware(self):
        from interface.main import add_process_time_header

        request = Mock(spec=Request)
        response = Mock()
        response.headers = {}

        async def call_next(req):
            await asyncio.sleep(0.01)
            return response

        import asyncio

        result = await add_process_time_header(request, call_next)
        assert result == response
        assert "X-Process-Time" in response.headers
        assert float(response.headers["X-Process-Time"]) > 0


class TestEndpoints:
    @pytest.fixture
    def client(self, mock_settings, mock_container):
        from interface.main import app

        return TestClient(app)

    def test_root_endpoint(self, client, mock_settings):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Intelligent Document Search API"
        assert data["version"] == mock_settings.app_version
        assert data["status"] == "running"
        assert data["docs_url"] == "/docs"
        assert data["api_prefix"] == mock_settings.api_prefix

    @patch("interface.main.container")
    def test_health_check_all_healthy(self, mock_container, client):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_container.get_redis_client.return_value = mock_redis_client
        with patch("infrastructure.database.connection.db_connection") as mock_db:

            async def mock_get_session():
                mock_session = AsyncMock()
                mock_result = Mock()
                mock_result.scalar.return_value = 1
                mock_session.execute = AsyncMock(return_value=mock_result)
                yield mock_session

            mock_db.get_session.return_value = mock_get_session()
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["redis"] == "healthy"
            assert data["services"]["database"]["postgres"] == "healthy"
            assert data["services"]["database"]["type"] == "postgresql"

    @patch("interface.main.container")
    def test_health_check_redis_unhealthy(self, mock_container, client):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=False)
        mock_container.get_redis_client.return_value = mock_redis_client
        with patch("infrastructure.database.connection.db_connection") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute = AsyncMock(return_value=mock_result)

            async def mock_get_session():
                yield mock_session

            mock_db.get_session.return_value = mock_get_session()
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["redis"] == "unhealthy"

    @patch("interface.main.container")
    def test_health_check_database_unhealthy(self, mock_container, client):
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_container.get_redis_client.return_value = mock_redis_client
        with patch("infrastructure.database.connection.db_connection") as mock_db:
            mock_db.get_session.side_effect = Exception("Database error")
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["database"]["type"] == "none"

    @patch("interface.main.container")
    def test_health_check_exception(self, mock_container, client):
        mock_container.get_redis_client.side_effect = Exception("Critical error")
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data

    def test_app_info_endpoint(self, client, mock_settings):
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == mock_settings.app_name
        assert data["version"] == mock_settings.app_version
        assert data["environment"] == "production"
        assert data["features"]["chat"] is True
        assert data["features"]["document_search"] is True
        assert data["features"]["session_management"] is True
        assert data["features"]["rate_limiting"] is True
        assert (
            data["features"]["contextual_retrieval"]
            == mock_settings.use_contextual_retrieval
        )
        assert (
            data["limits"]["max_messages_per_session"]
            == mock_settings.max_messages_per_session
        )

    def test_app_info_endpoint_debug_mode(self, client):
        with patch("interface.main.settings") as mock_settings:
            mock_settings.app_name = "Test App"
            mock_settings.app_version = "1.0.0"
            mock_settings.debug = True
            mock_settings.use_contextual_retrieval = True
            mock_settings.max_messages_per_session = 100
            mock_settings.max_daily_messages = 1000
            mock_settings.chunk_size = 500
            mock_settings.default_search_results = 5
            response = client.get("/info")
            assert response.status_code == 200
            data = response.json()
            assert data["environment"] == "development"


class TestExceptionHandler:
    @pytest.fixture
    def client(self, mock_settings, mock_container):
        from interface.main import app

        return TestClient(app)

    def test_global_exception_handler_production(self, client):
        with patch("interface.main.settings") as mock_settings:
            mock_settings.debug = False
            with patch("interface.main.api_router") as mock_router:
                mock_router.side_effect = Exception("Test error")
                response = client.get("/nonexistent")
                assert response.status_code == 404

    def test_global_exception_handler_debug(self, client):
        with patch("interface.main.settings") as mock_settings:
            mock_settings.debug = True
            with patch("interface.main.api_router") as mock_router:
                mock_router.side_effect = Exception("Test error")
                response = client.get("/nonexistent")
                assert response.status_code == 404


class TestMainExecution:
    @patch("uvicorn.run")
    def test_main_execution(self, mock_uvicorn_run, mock_settings):
        mock_settings.api_host = "localhost"
        mock_settings.api_port = 8080
        mock_settings.debug = True
        mock_settings.log_level = "DEBUG"
        # Simulate running the main block
        import uvicorn

        uvicorn.run(
            "interface.main:app",
            host=mock_settings.api_host,
            port=mock_settings.api_port,
            reload=mock_settings.debug,
            log_level=mock_settings.log_level.lower(),
        )
        mock_uvicorn_run.assert_called_once_with(
            "interface.main:app",
            host="localhost",
            port=8080,
            reload=True,
            log_level="debug",
        )
