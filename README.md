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

### Desenvolvimento
```bash
# Executar com uvicorn (desenvolvimento)
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ou executar o arquivo diretamente
poetry run python main.py
```

### Produção
```bash
# Executar com Gunicorn (produção)
poetry run gunicorn main:app -c gunicorn.conf.py
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

## Configuração com Nginx

Para máxima performance em produção, configure o nginx como proxy reverso:

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

## Documentação

A documentação interativa está disponível em:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testes

```bash
# Testar endpoint de pagamento
curl -X POST "http://localhost:8000/payments" \
     -H "Content-Type: application/json" \
     -d '{
       "correlationId": "4a7901b8-7d26-4d9d-aa19-4dc1c7cf60b3",
       "amount": 19.90
     }'

# Testar health check
curl http://localhost:8000/health
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
└── README.md           # Este arquivo
``` 