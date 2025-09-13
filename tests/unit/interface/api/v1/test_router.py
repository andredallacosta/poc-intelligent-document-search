import pytest
from fastapi import APIRouter

from interface.api.v1.router import api_router
from interface.api.v1.endpoints import chat


class TestAPIRouter:
    
    def test_api_router_creation(self):
        assert isinstance(api_router, APIRouter)
    
    def test_chat_router_included(self):
        # Verify that chat router is included in the main router
        included_routes = [route.path for route in api_router.routes]
        
        # Check that chat endpoints are included
        assert any("/chat/ask" in path for path in included_routes)
        assert any("/chat/health" in path for path in included_routes)
        assert any("/chat/models" in path for path in included_routes)
    
    def test_router_has_correct_routes(self):
        # Get all routes from the router
        routes = api_router.routes
        
        # Should have at least the chat routes
        assert len(routes) >= 3  # ask, health, models
        
        # Verify route methods
        route_methods = {}
        for route in routes:
            if hasattr(route, 'methods'):
                route_methods[route.path] = route.methods
        
        # Check specific endpoints and their methods
        chat_ask_found = False
        chat_health_found = False
        chat_models_found = False
        
        for path, methods in route_methods.items():
            if "/chat/ask" in path:
                assert "POST" in methods
                chat_ask_found = True
            elif "/chat/health" in path:
                assert "GET" in methods
                chat_health_found = True
            elif "/chat/models" in path:
                assert "GET" in methods
                chat_models_found = True
        
        assert chat_ask_found, "Chat ask endpoint not found"
        assert chat_health_found, "Chat health endpoint not found"
        assert chat_models_found, "Chat models endpoint not found"
