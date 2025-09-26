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

docker-build: ## 🐳 Build Docker image
	@echo "🐳 Building Docker image..."
	@./scripts/build.sh

docker-build-push: ## 🐳 Build and push Docker image
	@echo "🐳 Building and pushing Docker image..."
	@PUSH=true ./scripts/build.sh

docker-up: ## 🐳 Start development environment with Docker
	@echo "🐳 Starting development environment..."
	@docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "✅ Development environment started!"
	@echo "🔗 API: http://localhost:8000"
	@echo "🔗 Docs: http://localhost:8000/docs"
	@echo "🔗 Queue: http://localhost:8000/api/v1/queue/info"

docker-down: ## 🛑 Stop Docker environment
	@echo "🛑 Stopping development environment..."
	@docker-compose down

docker-logs: ## 📋 Show Docker logs
	@echo "📋 Showing Docker logs..."
	@docker-compose logs -f

docker-clean: ## 🧹 Clean Docker containers and images
	@echo "🧹 Cleaning Docker resources..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f

docker-prod: ## 🚀 Start production environment
	@echo "🚀 Starting production environment..."
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production environment started!"

docker-prod-logs: ## 📋 Show production logs
	@docker-compose -f docker-compose.prod.yml logs -f

docker-prod-down: ## 🛑 Stop production environment
	@echo "🛑 Stopping production environment..."
	@docker-compose -f docker-compose.prod.yml down

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
# LOCALSTACK DEVELOPMENT
# =============================================================================

localstack-setup: ## Setup LocalStack S3 for development
	@echo "🚀 Setting up LocalStack S3..."
	@if ! command -v aws >/dev/null 2>&1; then \
		echo "❌ AWS CLI not found. Install with: pip install awscli"; \
		exit 1; \
	fi
	@./scripts/setup_localstack.sh

localstack-test: ## Test document ingestion with real documents from /documents folder
	@echo "🧪 Testing document ingestion with real documents..."
	@if ! python -c "import aiohttp" >/dev/null 2>&1; then \
		echo "❌ Missing dependencies. Install with: pip install aiohttp"; \
		exit 1; \
	fi
	@cd /home/andre/Projects/poc-intelligent-document-search && python scripts/test_real_documents.py

localstack-test-search: ## Test search quality with real documents
	@echo "🎯 Testing search quality with real documents..."
	@if ! python -c "import aiohttp" >/dev/null 2>&1; then \
		echo "❌ Missing dependencies. Install with: pip install aiohttp"; \
		exit 1; \
	fi
	@cd /home/andre/Projects/poc-intelligent-document-search && python scripts/test_search_quality.py

localstack-status: ## Check LocalStack S3 status
	@echo "📊 Checking LocalStack S3 status..."
	@if command -v aws >/dev/null 2>&1; then \
		AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4566 s3 ls; \
	else \
		echo "❌ AWS CLI not found. Install with: pip install awscli"; \
	fi

# =============================================================================
# REDIS QUEUE MANAGEMENT
# =============================================================================

worker: ## 🔄 Start Redis worker for document processing
	@echo "🔄 Starting Redis worker for document processing..."
	@python worker.py

worker-all: ## 🔄 Start Redis worker for all queues
	@echo "🔄 Starting Redis worker for all queues..."
	@python worker.py --all

worker-cleanup: ## 🧹 Start Redis worker only for cleanup tasks
	@echo "🧹 Starting Redis worker for cleanup tasks..."
	@python worker.py --queues cleanup_tasks

worker-verbose: ## 🔄 Start Redis worker with verbose logging
	@echo "🔄 Starting Redis worker with verbose logging..."
	@python worker.py --verbose

queue-info: ## 📊 Show Redis queue information
	@echo "📊 Redis Queue Information:"
	@curl -s http://localhost:8000/api/v1/queue/info | python -m json.tool || echo "Start server first: make dev"

queue-health: ## 🏥 Check Redis queue health
	@echo "🏥 Redis Queue Health Check:"
	@curl -s http://localhost:8000/api/v1/queue/health | python -m json.tool || echo "Start server first: make dev"

cleanup-s3: ## 🗑️ Schedule S3 cleanup task
	@echo "🗑️ Scheduling S3 cleanup task..."
	@python scripts/cleanup_scheduler.py --s3-cleanup

cleanup-orphaned: ## 🗑️ Schedule orphaned files cleanup
	@echo "🗑️ Scheduling orphaned files cleanup..."
	@python scripts/cleanup_scheduler.py --orphaned-files

cleanup-daily: ## 🗑️ Schedule daily cleanup (S3 + orphaned)
	@echo "🗑️ Scheduling daily cleanup..."
	@python scripts/cleanup_scheduler.py --daily


# =============================================================================
# DEPLOYMENT & OPERATIONS
# =============================================================================

deploy: ## 🚀 Deploy to production
	@echo "🚀 Deploying to production..."
	@./scripts/deploy.sh

backup: ## 💾 Create backup of critical data
	@echo "💾 Creating backup..."
	@./scripts/backup.sh

health-check: ## 🏥 Check health of all services
	@echo "🏥 Checking service health..."
	@./scripts/health-check.sh

# =============================================================================
# SHORTCUTS
# =============================================================================

up: docker-up ## 🚀 Start all services (auto-runs migrations)
down: docker-down ## 🛑 Stop all services  
restart: docker-down docker-up ## 🔄 Restart all services (auto-runs migrations)
fresh-start: docker-down docker-build docker-up ## 🆕 Fresh start: Clean rebuild with auto-migrations
logs-api: logs ## Alias for logs

dev-full: docker-up ## 🔧 Start full development environment (Docker + API + Workers)
	@echo "🔧 Full development environment ready!"

prod-deploy: docker-build deploy ## 🚀 Build and deploy to production
	@echo "🚀 Build and deploy completed!"

status: ## 📊 Show status of all services
	@echo "📊 Service Status:"
	@echo ""
	@echo "🐳 Docker Containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not running"
	@echo ""
	@echo "🏥 Health Check:"
	@./scripts/health-check.sh 2>/dev/null || echo "Health check failed"
