# Dockerfile com Poetry configurado corretamente
FROM python:3.12-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar Poetry
RUN pip install poetry

# Configurar Poetry para criar ambiente virtual no projeto
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Copiar arquivos de dependências
COPY pyproject.toml ./

# Instalar dependências (cria .venv durante o build)
RUN poetry install --only=main

# Copiar código da aplicação
COPY main.py ./

# Expor porta da aplicação
EXPOSE 8080

# Comando para iniciar a aplicação (poetry run encontra o ambiente virtual)
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 