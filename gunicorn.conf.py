# Configuração do Gunicorn para produção com nginx
# Otimizada para alta performance

import multiprocessing
import os

# Configuração do servidor
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Configurações de timeout
timeout = 30
keepalive = 2

# Configurações de performance
preload_app = True
worker_tmp_dir = "/dev/shm"

# Configurações de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Configurações de segurança
limit_request_line = 0
limit_request_fields = 100
limit_request_field_size = 8190

# Configurações de processo
user = os.getenv("USER", "nobody")
group = os.getenv("GROUP", "nobody")
tmp_upload_dir = None

# Configurações de daemon
daemon = False
pidfile = None
umask = 0
user = None
group = None

# Configurações de graceful restart
graceful_timeout = 30 