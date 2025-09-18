# Intelligent Document Search API v2.0 - Makefile
# Clean Architecture with PostgreSQL + pgvector

.PHONY: help install dev-install clean lint format type-check test test-unit test-integration test-e2e test-coverage
.PHONY: docker-build docker-up docker-down docker-logs docker-clean
.PHONY: db-up db-down db-migrate db-reset db-shell
.PHONY: run dev check-deps security-check

# Default target
help: ## Show this help message
	@echo "Intelligent Document Search API v2.0 - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# INSTALLATION & SETUP
# =============================================================================

install: ## Install production dependencies
	@echo "📦 Installing production dependencies..."
	pip install -e .

dev-install: ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	pip install -e ".[dev]"

clean: ## Clean build artifacts and cache
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: ## Run all linting tools
	@echo "🔍 Running linting tools..."
	@echo "  → flake8..."
	flake8 interface/ domain/ infrastructure/ application/ shared/
	@echo "  → black (check only)..."
	black --check interface/ domain/ infrastructure/ application/ shared/
	@echo "  → isort (check only)..."
	isort --check-only interface/ domain/ infrastructure/ application/ shared/
	@echo "✅ Linting completed!"

format: ## Format code with black and isort
	@echo "🎨 Formatting code..."
	@echo "  → black..."
	black interface/ domain/ infrastructure/ application/ shared/
	@echo "  → isort..."
	isort interface/ domain/ infrastructure/ application/ shared/
	@echo "✅ Code formatted!"

type-check: ## Run mypy type checking
	@echo "🔍 Running type checks..."
	mypy interface/ domain/ infrastructure/ application/ shared/
	@echo "✅ Type checking completed!"

check: lint type-check ## Run all code quality checks

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v -m "unit"

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v -m "integration"

test-e2e: ## Run end-to-end tests only
	@echo "🧪 Running e2e tests..."
	pytest tests/e2e/ -v -m "e2e"

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	pytest tests/ --cov=interface --cov=domain --cov=infrastructure --cov=application --cov=shared --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated in htmlcov/"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "👀 Running tests in watch mode..."
	ptw tests/ -- -v

# =============================================================================
# APPLICATION MANAGEMENT
# =============================================================================

run: ## Start the API server (development)
	@echo "🚀 Starting API server..."
	@echo "📋 Make sure you have activated your virtual environment:"
	@echo "   source .venv/bin/activate"
	@echo ""
	python -m interface.main

dev: ## Start the API server with auto-reload
	@echo "🚀 Starting API server with auto-reload..."
	@echo "📋 Make sure you have activated your virtual environment:"
	@echo "   source .venv/bin/activate"
	@echo ""
	uvicorn interface.main:app --host 0.0.0.0 --port 8000 --reload

# =============================================================================
# DOCKER MANAGEMENT
# =============================================================================

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t intelligent-document-search:latest .

docker-up: ## Start all services with Docker Compose
	@echo "🐳 Starting all services..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "✅ Services started!"
	@echo "🔗 API: http://localhost:8000"
	@echo "📚 Docs: http://localhost:8000/docs"

docker-down: ## Stop all Docker services
	@echo "🐳 Stopping all services..."
	docker-compose down

docker-logs: ## Show Docker logs
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

docker-clean: ## Clean Docker containers and images
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

db-up: ## Start database services only
	@echo "🗄️ Starting database services..."
	docker-compose up -d postgres redis
	@echo "⏳ Waiting for databases to be ready..."
	@sleep 5
	@echo "✅ Databases ready!"

db-down: ## Stop database services
	@echo "🗄️ Stopping database services..."
	docker-compose stop postgres redis

db-migrate: ## Run database migrations
	@echo "🗄️ Running database migrations..."
	@echo "📋 Make sure databases are running (make db-up)"
	alembic upgrade head
	@echo "✅ Migrations completed!"

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "🗄️ Resetting database..."
	docker-compose down -v postgres
	docker-compose up -d postgres
	@sleep 5
	alembic upgrade head
	@echo "✅ Database reset completed!"

db-shell: ## Connect to PostgreSQL shell
	@echo "🗄️ Connecting to PostgreSQL..."
	docker exec -it poc-postgres psql -U postgres -d intelligent_document_search

# =============================================================================
# SECURITY & DEPENDENCIES
# =============================================================================

check-deps: ## Check for dependency vulnerabilities
	@echo "🔒 Checking dependencies for vulnerabilities..."
	pip-audit

security-check: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r interface/ domain/ infrastructure/ application/ shared/

# =============================================================================
# HEALTH CHECKS
# =============================================================================

health: ## Check API health
	@echo "🏥 Checking API health..."
	curl -s http://localhost:8000/health | jq .

ping: ## Ping API endpoints
	@echo "🏓 Pinging API endpoints..."
	@echo "Root endpoint:"
	curl -s http://localhost:8000/ | jq .
	@echo "\nHealth endpoint:"
	curl -s http://localhost:8000/health | jq .

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

docs: ## Open API documentation
	@echo "📚 Opening API documentation..."
	@echo "🔗 Interactive docs: http://localhost:8000/docs"
	@echo "🔗 ReDoc: http://localhost:8000/redoc"

logs: ## Show application logs (if running with Docker)
	@echo "📋 Showing application logs..."
	docker-compose logs -f intelligent-document-search

# =============================================================================
# SHORTCUTS
# =============================================================================

up: docker-up ## Alias for docker-up
down: docker-down ## Alias for docker-down
restart: docker-down docker-up ## Restart all services
logs-api: logs ## Alias for logs
