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

logs-nginx: ## Mostrar logs do Nginx
	@echo "📋 Logs do Nginx:"
	docker-compose -f $(COMPOSE_FILE) logs -f nginx

logs-apis: ## Mostrar logs das APIs (para debug interno)
	@echo "📋 Logs das APIs (api-1 e api-2):"
	docker-compose -f $(COMPOSE_FILE) logs -f api-1 api-2

status: ## Mostrar status dos containers
	@echo "📊 Status dos containers:"
	docker-compose -f $(COMPOSE_FILE) ps

clean: ## Limpar containers e imagens
	@echo "🧹 Limpando containers e imagens..."
	docker-compose -f $(COMPOSE_FILE) down --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

health-check: ## Testar a aplicação via Load Balancer
	@echo "🧪 Testando Load Balancer (porta 9999)..."
	@curl -s http://localhost:9999/health | jq '.' || echo "❌ Load Balancer não está respondendo"

payment-test: ## Testar endpoints de pagamento via Load Balancer
	@echo "🧪 Testando POST /payments via Load Balancer (distribuindo entre API 1 e API 2)..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@for i in 1; do \
		echo "Requisição $$i:"; \
		curl -X POST http://localhost:9999/payments \
			-H "Content-Type: application/json" \
			-d '{"correlationId": "'$$(uuidgen)'", "amount": 10.25}' \
			-w "Status: %{http_code}\n" \
			-s; \
		echo ""; \
	done


summary-test:
	@echo "📊 Testando GET /payments-summary via Load Balancer..."
	@curl -s "http://localhost:9999/payments-summary?from=2025-08-01T00:00:00.000Z&to=2025-08-31T23:59:59.999Z" | jq '.' || echo "❌ Erro na consulta"


admin-summary-test: ## Testar endpoint /admin/payments-summary nos processadores externos
	@echo "📊 Testando processador padrão"
	@curl -s "http://localhost:8001/admin/payments-summary?from=2025-08-01T00:00:00.000Z&to=2025-08-31T23:59:59.000Z" --header 'X-Rinha-Token: 123' | jq '.' || echo "❌ Processador padrão não está respondendo"
	@echo ""
	@echo "📊 Testando processador de fallback"
	@curl -s "http://localhost:8002/admin/payments-summary?from=2025-08-01T00:00:00.000Z&to=2025-08-31T23:59:59.000Z" --header 'X-Rinha-Token: 123' | jq '.' || echo "❌ Processador de fallback não está respondendo"

purge-payments:
	@echo "🧪 Testando POST /purge-payments via Load Balancer..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@curl -X POST http://localhost:9999/purge-payments \
		-H "X-Rinha-Token: 123"

admin-purge-payments:
	@echo "🧪 Testando POST /admin/purge-payments via Load Balancer..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@curl -X POST http://localhost:8001/admin/purge-payments \
		-H "X-Rinha-Token: 123"
	@curl -X POST http://localhost:8002/admin/purge-payments \
		-H "X-Rinha-Token: 123"


summary-all-test: summary-test admin-summary-test ## Executar todos os testes de summary
	@echo "✅ Todos os testes de summary foram executados"


dev: ## Executar aplicação local em modo desenvolvimento
	@echo "🚀 Executando aplicação local na porta 8080..."
	poetry run python app/main.py


dev-docker: ## Executar aplicação Docker com hot reload
	@echo "🚀 Executando aplicação Docker com hot reload..."
	docker-compose -f $(COMPOSE_FILE) up --build 