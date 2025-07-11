# Makefile para facilitar a execução da aplicação

.PHONY: help build up down restart logs status clean test

# Configurações
COMPOSE_FILE = docker-compose.yml
PROJECT_NAME = rinha-backend

# Comando padrão
help: ## Mostrar ajuda
	@echo "Comandos disponíveis:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Construir as imagens Docker
	@echo "🏗️  Construindo imagens Docker..."
	docker-compose -f $(COMPOSE_FILE) build --no-cache

up: ## Subir os containers
	@echo "🚀 Iniciando aplicação..."
	docker-compose -f $(COMPOSE_FILE) up -d

down: ## Parar os containers
	@echo "🛑 Parando aplicação..."
	docker-compose -f $(COMPOSE_FILE) down

restart: down up ## Reiniciar a aplicação

logs: ## Mostrar logs dos containers
	@echo "📋 Logs da aplicação:"
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api1: ## Mostrar logs da API 1
	@echo "📋 Logs da API 1:"
	docker-compose -f $(COMPOSE_FILE) logs -f api-1

logs-api2: ## Mostrar logs da API 2
	@echo "📋 Logs da API 2:"
	docker-compose -f $(COMPOSE_FILE) logs -f api-2



status: ## Mostrar status dos containers
	@echo "📊 Status dos containers:"
	docker-compose -f $(COMPOSE_FILE) ps

clean: ## Limpar containers e imagens
	@echo "🧹 Limpando containers e imagens..."
	docker-compose -f $(COMPOSE_FILE) down --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

test-api: ## Testar as APIs
	@echo "🧪 Testando API 1 (porta 8003)..."
	@curl -s http://localhost:8003/health | jq '.' || echo "❌ API 1 não está respondendo"
	@echo ""
	@echo "🧪 Testando API 2 (porta 8004)..."
	@curl -s http://localhost:8004/health | jq '.' || echo "❌ API 2 não está respondendo"

test-payments: ## Testar endpoints de pagamento
	@echo "🧪 Testando POST /payments na API 1..."
	@curl -X POST http://localhost:8003/payments \
		-H "Content-Type: application/json" \
		-d '{"correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3", "amount": 19.90}' \
		| jq '.' || echo "❌ Teste falhou"
	@echo ""
	@echo "🧪 Testando POST /payments na API 2..."
	@curl -X POST http://localhost:8004/payments \
		-H "Content-Type: application/json" \
		-d '{"correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3", "amount": 19.90}' \
		| jq '.' || echo "❌ Teste falhou"

dev: ## Executar aplicação local em modo desenvolvimento
	@echo "🚀 Executando aplicação local na porta 8080..."
	poetry run python main.py

dev-gunicorn: ## Executar aplicação local com Gunicorn
	@echo "🚀 Executando aplicação local com Gunicorn na porta 8080..."
	poetry run gunicorn main:app -c gunicorn.conf.py 