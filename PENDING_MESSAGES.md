# Sistema de Pending Messages Recovery

## Problema Resolvido

Quando `process_payment` retorna `False` (ambos processors indisponíveis), a mensagem fica "pending" no Redis Streams e não é reprocessada automaticamente, podendo ser perdida.

## Solução Implementada

### 1. **Mantém Lógica Original**
- ✅ Só faz `xack` quando `processed=True` (sucesso)
- ❌ **NÃO** faz `xack` quando `processed=False` (ambos indisponíveis)
- ❌ **NÃO** faz `xack` quando há exceção

### 2. **Pending Messages Reclaim**
```python
async def _reclaim_pending_messages(redis) -> None:
    # Busca mensagens pending há mais de 30 segundos
    pending_info = await redis.xpending(PAYMENTS_STREAM, PAYMENTS_CONSUMER_GROUP, count=10)
    
    for pending in pending_info:
        if idle_time > PENDING_TIMEOUT_MS:
            # Reclama a mensagem para reprocessamento
            claimed = await redis.xclaim(
                PAYMENTS_STREAM, PAYMENTS_CONSUMER_GROUP, CONSUMER_NAME,
                min_idle_time=PENDING_TIMEOUT_MS, message_ids=[message_id]
            )
            # Reprocessa a mensagem
            await _handle_messages(entries)
```

### 3. **Integração no Worker**
- **A cada 10 loops**: verifica mensagens pending
- **Timeout configurável**: `WORKER_PENDING_TIMEOUT_MS=30000` (30s)
- **Não bloqueia**: processamento normal continua

## Como Funciona

### Fluxo Normal
1. **Mensagem lida** → `xreadgroup`
2. **Processamento** → `process_payment()`
3. **Sucesso** → `xack` (confirma)
4. **Falha** → fica pending (será reclamada)

### Reclaim de Pending
1. **A cada 10 loops** → verifica pending
2. **Se > 30s pending** → reclama mensagem
3. **Reprocessa** → nova tentativa
4. **Sucesso** → `xack` / **Falha** → fica pending novamente

## Benefícios

- ✅ **Não perde mensagens** que falharam temporariamente
- ✅ **Reprocessamento automático** após timeout
- ✅ **Mantém lógica existente** sem quebrar
- ✅ **Performance preservada** (verifica só a cada 10 loops)

## Configuração

```yaml
# docker-compose.yml
environment:
  - WORKER_PENDING_TIMEOUT_MS=30000  # 30 segundos
```

## Cenários de Uso

| Situação | Ação | Resultado |
|----------|------|-----------|
| Default OK | Processa + xack | ✅ Confirmado |
| Fallback OK | Processa + xack | ✅ Confirmado |
| Ambos indisponíveis | Não ack | ⏳ Fica pending, será reclamado |
| Erro de código | Não ack | ⏳ Fica pending, será reclamado |
| Timeout 30s | Reclaim + retry | 🔄 Nova tentativa |

## Monitoramento

### Logs para Acompanhar
```bash
# Mensagens reclamadas
"Reclaiming pending message X from consumer Y (idle: Zms)"

# Mensagens reprocessadas
"Successfully claimed message X"

# Contagem de pending
"Found N pending messages to check"
```

### Redis Commands para Debug
```bash
# Ver mensagens pending
XPENDING payments-stream payments-workers

# Ver detalhes de um consumer
XPENDING payments-stream payments-workers - + 10 api-1

# Forçar claim manual (se necessário)
XCLAIM payments-stream payments-workers api-1 30000 message-id
```

## Vantagens sobre Outras Soluções

- **vs Always ACK**: Não perde mensagens que realmente falharam
- **vs Dead Letter Queue**: Mais simples, usa recursos nativos do Redis
- **vs Retry Complexo**: Mantém lógica original, sem quebrar health check

## Resultado

Mensagens que retornam `False` (ambos processors indisponíveis) agora são **automaticamente reprocessadas** após 30 segundos, garantindo que nenhuma transação seja perdida! 🎯
