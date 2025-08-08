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

payment-test: ## Testar endpoints de pagamento via Load Balancer (uso: make payment-test AMOUNT=10.25)
	@if [ -z "$(AMOUNT)" ]; then \
		echo "❌ Erro: AMOUNT é obrigatório. Use: make payment-test AMOUNT=10.25"; \
		exit 1; \
	fi
	@echo "🧪 Testando POST /payments via Load Balancer (distribuindo entre API 1 e API 2)..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@echo "💰 Valor do pagamento: $(AMOUNT)"
	@for i in 1; do \
		echo "Requisição $$i:"; \
		curl -X POST http://localhost:9999/payments \
			-H "Content-Type: application/json" \
			-d '{"correlationId": "'$$(uuidgen)'", "amount": $(AMOUNT)}' \
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

purge-payments: ## Testar endpoint de purge via Load Balancer
	@echo "🧪 Testando POST /purge-payments via Load Balancer..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@curl -X POST http://localhost:9999/purge-payments \
		-H "X-Rinha-Token: 123" -w "Status: %{http_code}\n" -s

admin-purge-payments: ## Testar endpoint de purge nos processadores externos
	@echo "🧪 Testando POST /purge-payments nos processadores externos..."
	@echo "📝 Esperado: HTTP 204 No Content (sem corpo de resposta)"
	@echo "📊 Testando processador padrão (porta 8001):"
	@curl -X POST http://localhost:8001/admin/purge-payments \
		-H "X-Rinha-Token: 123" -w "Status: %{http_code}\n" -s
	@echo ""
	@echo "📊 Testando processador de fallback (porta 8002):"
	@curl -X POST http://localhost:8002/admin/purge-payments \
		-H "X-Rinha-Token: 123" -w "Status: %{http_code}\n" -s

purge-all: purge-payments admin-purge-payments

admin-set-default-delay: ## Configurar delay no processador padrão (uso: make admin-set-default-delay DELAY=1000)
	@if [ -z "$(DELAY)" ]; then \
		echo "❌ Erro: DELAY é obrigatório. Use: make admin-set-default-delay DELAY=1000"; \
		exit 1; \
	fi
	@echo "⚙️  Configurando delay de $(DELAY)ms no processador padrão (porta 8001)..."
	@curl -X PUT http://localhost:8001/admin/configurations/delay \
		-H "Content-Type: application/json" \
		-H "X-Rinha-Token: 123" \
		-d '{"delay": $(DELAY)}' \
		-w "Status: %{http_code}\n" -s

admin-set-fallback-delay: ## Configurar delay no processador de fallback (uso: make admin-set-fallback-delay DELAY=1000)
	@if [ -z "$(DELAY)" ]; then \
		echo "❌ Erro: DELAY é obrigatório. Use: make admin-set-fallback-delay DELAY=1000"; \
		exit 1; \
	fi
	@echo "⚙️  Configurando delay de $(DELAY)ms no processador de fallback (porta 8002)..."
	@curl -X PUT http://localhost:8002/admin/configurations/delay \
		-H "Content-Type: application/json" \
		-H "X-Rinha-Token: 123" \
		-d '{"delay": $(DELAY)}' \
		-w "Status: %{http_code}\n" -s

admin-set-default-failure: ## Configurar failure no processador padrão (uso: make admin-set-default-failure FAILURE=true)
	@if [ -z "$(FAILURE)" ]; then \
		echo "❌ Erro: FAILURE é obrigatório. Use: make admin-set-default-failure FAILURE=true ou FAILURE=false"; \
		exit 1; \
	fi
	@if [ "$(FAILURE)" != "true" ] && [ "$(FAILURE)" != "false" ]; then \
		echo "❌ Erro: FAILURE deve ser 'true' ou 'false'. Use: make admin-set-default-failure FAILURE=true ou FAILURE=false"; \
		exit 1; \
	fi
	@echo "⚙️  Configurando failure=$(FAILURE) no processador padrão (porta 8001)..."
	@curl -X PUT http://localhost:8001/admin/configurations/failure \
		-H "Content-Type: application/json" \
		-H "X-Rinha-Token: 123" \
		-d '{"failure": $(FAILURE)}' \
		-w "Status: %{http_code}\n" -s

admin-set-fallback-failure: ## Configurar failure no processador de fallback (uso: make admin-set-fallback-failure FAILURE=true)
	@if [ -z "$(FAILURE)" ]; then \
		echo "❌ Erro: FAILURE é obrigatório. Use: make admin-set-fallback-failure FAILURE=true ou FAILURE=false"; \
		exit 1; \
	fi
	@if [ "$(FAILURE)" != "true" ] && [ "$(FAILURE)" != "false" ]; then \
		echo "❌ Erro: FAILURE deve ser 'true' ou 'false'. Use: make admin-set-fallback-failure FAILURE=true ou FAILURE=false"; \
		exit 1; \
	fi
	@echo "⚙️  Configurando failure=$(FAILURE) no processador de fallback (porta 8002)..."
	@curl -X PUT http://localhost:8002/admin/configurations/failure \
		-H "Content-Type: application/json" \
		-H "X-Rinha-Token: 123" \
		-d '{"failure": $(FAILURE)}' \
		-w "Status: %{http_code}\n" -s


summary-all-test: summary-test admin-summary-test ## Executar todos os testes de summary
	@echo "✅ Todos os testes de summary foram executados"


dev: ## Executar aplicação local em modo desenvolvimento
	@echo "🚀 Executando aplicação local na porta 8080..."
	poetry run python app/main.py


dev-docker: ## Executar aplicação Docker com hot reload
	@echo "🚀 Executando aplicação Docker com hot reload..."
	docker-compose -f $(COMPOSE_FILE) up --build 