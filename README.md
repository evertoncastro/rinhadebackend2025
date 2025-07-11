# Rinha de Backend 2025 - API de Pagamentos

API de pagamentos com alta performance construída com FastAPI, otimizada para rodar com nginx.

## Funcionalidades

- ✅ Rota POST `/payments` para processar pagamentos
- ✅ Validação robusta de dados com Pydantic
- ✅ Configuração otimizada para produção com Gunicorn + Uvicorn
- ✅ Health check endpoint
- ✅ Documentação automática com Swagger UI

## Requisitos

- Python 3.12+
- Poetry

## Instalação

```bash
# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell
```

## Execução

### Local - Desenvolvimento
```bash
# Executar com uvicorn (desenvolvimento)
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Ou executar o arquivo diretamente
poetry run python main.py

# Usando o Makefile
make dev
```

### Local - Produção
```bash
# Executar com Gunicorn (produção)
poetry run gunicorn main:app -c gunicorn.conf.py

# Usando o Makefile
make dev-gunicorn
```

### Docker - Orquestração das APIs
```bash
# Construir as imagens
make build

# Subir os containers (2 instâncias da API)
make up

# Verificar status
make status

# Ver logs
make logs

# Testar as APIs
make test

# Testar endpoints de pagamento
make test-payments

# Parar os containers
make down

# Limpeza completa
make clean
```

## Endpoints

### POST /payments
Processa um pagamento.

**Corpo da requisição:**
```json
{
    "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
    "amount": 19.90
}
```

**Resposta (200 OK):**
```json
{
    "status": "success",
    "message": "Pagamento processado com sucesso",
    "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
    "amount": 19.90
}
```

**Validações:**
- `correlationId`: obrigatório, deve ser um UUID válido
- `amount`: obrigatório, deve ser maior que 0

### GET /health
Health check da aplicação.

**Resposta (200 OK):**
```json
{
    "status": "healthy"
}
```

## Arquitetura Docker

### Configuração de Containers

- **API 1**: Roda na porta 8003 (mapeada da porta interna 8080)
- **API 2**: Roda na porta 8004 (mapeada da porta interna 8080)
- **Rede**: rinha-network (isolada de outras redes)

### Portas Disponíveis

- **Local**: http://localhost:8080
- **API 1**: http://localhost:8003
- **API 2**: http://localhost:8004

### Configuração Simples

**Dockerfile:**
- **Imagem base**: Python 3.12 slim
- **Poetry**: Gerenciamento de dependências com pyproject.toml
- **Ambiente virtual**: Criado durante o build automaticamente
- **Execução**: `poetry run` encontra o ambiente virtual correto
- **Servidor**: Uvicorn (simples e eficiente)

**Docker Compose:**
- **Dois serviços**: api-1 e api-2
- **Build simples**: Apenas context
- **Port mapping**: 8003:8080 e 8004:8080
- **Rede própria**: rinha-network (bridge)

> 📝 **Nota**: Tanto o Dockerfile quanto o docker-compose.yml estão em suas versões mais simples para facilitar o aprendizado. Otimizações podem ser adicionadas gradualmente.

## Documentação

A documentação interativa está disponível em:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testes

### Localmente (porta 8080)
```bash
# Testar endpoint de pagamento
curl -X POST "http://localhost:8080/payments" \
     -H "Content-Type: application/json" \
     -d '{
       "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
       "amount": 19.90
     }'

# Testar health check
curl http://localhost:8080/health
```

### Docker - Instâncias Específicas
```bash
# Testar API 1 (porta 8003)
curl -X POST "http://localhost:8003/payments" \
     -H "Content-Type: application/json" \
     -d '{
       "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
       "amount": 19.90
     }'

# Testar API 2 (porta 8004)
curl -X POST "http://localhost:8004/payments" \
     -H "Content-Type: application/json" \
     -d '{
       "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
       "amount": 19.90
     }'

# Health check das APIs
curl http://localhost:8003/health
curl http://localhost:8004/health
```

### Usando Make
```bash
# Testar todos os endpoints
make test

# Testar especificamente os endpoints de pagamento
make test-payments
```

## Configurações de Performance

- **Gunicorn**: Configurado com workers otimizados baseados no número de CPUs
- **Uvicorn Workers**: Utiliza workers assíncronos para máxima concorrência
- **Pydantic**: Validação rápida de dados com configurações otimizadas
- **Memory Optimization**: Uso de `/dev/shm` para arquivos temporários

## Estrutura do Projeto

```
.
├── main.py              # Aplicação FastAPI
├── gunicorn.conf.py     # Configuração do Gunicorn
├── pyproject.toml       # Dependências e configuração do Poetry
├── Dockerfile           # Imagem Docker simples
├── docker-compose.yml   # Orquestração de containers
├── .dockerignore       # Arquivos ignorados no build Docker
├── Makefile            # Comandos automatizados
└── README.md           # Este arquivo
``` 