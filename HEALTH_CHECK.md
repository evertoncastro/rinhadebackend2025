# Sistema de Health Check para Processors

## Visão Geral

Este sistema implementa um cache compartilhado de health check para os processors de pagamento, permitindo roteamento inteligente entre `default` (5% taxa) e `fallback` (15% taxa) baseado na saúde dos serviços.

## Funcionamento

### 1. Cache Compartilhado via Redis
- **TTL**: 5 segundos (respeita rate limit de 1 chamada/5s)
- **Lock Distribuído**: Evita que múltiplas instâncias façam a mesma chamada
- **Chaves**: `health:default`, `health:fallback`, `health_lock:default`, `health_lock:fallback`

### 2. Roteamento Inteligente
O `process_payment` decide qual processor usar:

```python
# Prioridade: default → fallback → nenhum
if default_ok is True:
    chosen = "default"      # 5% taxa
elif fallback_ok is True:
    chosen = "fallback"     # 15% taxa
else:
    return False            # Ambos indisponíveis, evita gargalo
```

### 3. Poller Opcional
- **Controle**: Variável `HEALTH_POLL_ENABLED`
- **Recomendação**: Habilitar apenas em **UMA** instância (ex: `api-1`)
- **Frequência**: A cada 5 segundos
- **Objetivo**: Manter cache quente sem estourar rate limit

## Configuração

### Docker Compose
```yaml
api-1:
  environment:
    - HEALTH_POLL_ENABLED=true    # ✅ Habilita poller

api-2:
  environment:
    # HEALTH_POLL_ENABLED ausente = false (padrão)
```

### Variáveis de Ambiente
```bash
HEALTH_POLL_ENABLED=false    # Padrão: sem poller
HEALTH_TTL_SECONDS=5         # Padrão: 5 segundos
```

## Fluxo de Decisão

1. **Recebimento**: Endpoint `/payments` apenas adiciona no stream (inalterado)
2. **Processamento**: Worker chama `process_payment()`
3. **Health Check**: Consulta cache Redis (com lock se necessário)
4. **Seleção**: Escolhe processor baseado na saúde
5. **Execução**: Envia para processor escolhido ou retorna False

## Benefícios

- ✅ **Menor Custo**: Prioriza processor default (5% vs 15%)
- ✅ **Resiliência**: Fallback automático quando default falha
- ✅ **Rate Limit**: Respeita limite de 1 chamada/5s
- ✅ **Compartilhado**: Cache entre todas as instâncias
- ✅ **Performance**: Evita requests desnecessários

## Monitoramento

### Redis Keys
```bash
# Health status
health:default     # {"failing": false, "minResponseTime": 100, "ts": 1234567890}
health:fallback    # {"failing": false, "minResponseTime": 150, "ts": 1234567890}

# Locks (expiram automaticamente)
health_lock:default
health_lock:fallback
```

### Logs
- Health check falhando: `Processor unavailable`
- Rate limit atingido: Cache marcado como `failing: true`
- Lock adquirido: Apenas uma instância atualiza por vez

## Troubleshooting

### Cache não atualiza
- Verificar se Redis está acessível
- Confirmar se `HEALTH_POLL_ENABLED=true` em uma instância
- Verificar logs de erro no health check

### Rate Limit atingido
- Normal: Sistema funciona com cache existente
- Cache expira em 5s automaticamente
- Lock garante que apenas uma instância chama por vez

### Performance
- Cache TTL de 5s é otimizado para rate limit
- Lock distribuído evita chamadas duplicadas
- Poller opcional mantém cache quente
