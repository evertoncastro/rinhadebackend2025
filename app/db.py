import os
import asyncpg
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://payments_user:payments_password@localhost:5432/payments_db")

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    assert _pool is not None
    return _pool

@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection

async def init_db():
    async with get_connection() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                correlation_id VARCHAR(100) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                requested_at TIMESTAMP NOT NULL,
                processor VARCHAR(10) NOT NULL DEFAULT 'default'
            )
        ''')
        
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_correlation_id 
            ON payments (correlation_id)
        ''')
        
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_processor 
            ON payments (processor)
        ''')
        

async def save_payment(correlation_id: str, amount: float, requested_at: datetime, processor: str = "default") -> Optional[int]:
    try:
        async with get_connection() as conn:
            if requested_at.tzinfo is None:
                utc_datetime = requested_at
            else:
                utc_datetime = requested_at.astimezone(timezone.utc).replace(tzinfo=None)
            
            row = await conn.fetchrow('''
                INSERT INTO payments (correlation_id, amount, requested_at, processor)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', correlation_id, amount, utc_datetime, processor)
            
            return row['id'] if row else None
            
    except asyncpg.UniqueViolationError:
        return None
    except Exception as e:
        raise e

async def get_payment_by_correlation_id(correlation_id: str) -> Optional[Dict[str, Any]]:
    async with get_connection() as conn:
        row = await conn.fetchrow('''
            SELECT id, correlation_id, amount, requested_at, processor
            FROM payments
            WHERE correlation_id = $1
        ''', correlation_id)
        
        return dict(row) if row else None

async def get_all_payments() -> List[Dict[str, Any]]:
    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT id, correlation_id, amount, requested_at, processor
            FROM payments
            ORDER BY requested_at DESC
        ''')
        
        return [dict(row) for row in rows]

async def get_payments_by_processor(processor: str) -> List[Dict[str, Any]]:

    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT id, correlation_id, amount, requested_at, processor
            FROM payments
            WHERE processor = $1
            ORDER BY requested_at DESC
        ''', processor)
        
        return [dict(row) for row in rows]

async def get_payments_summary(from_datetime: Optional[datetime] = None, to_datetime: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get payment summary by processor within optional date range.
    """
    async with get_connection() as conn:
        all_processors = ["default", "fallback"]
        
        query = '''
            SELECT 
                processor,
                COUNT(*) as total_requests,
                SUM(amount) as total_amount
            FROM payments
        '''
        
        params = []
        conditions = []
        
        if from_datetime:
            conditions.append("requested_at >= $1")
            params.append(from_datetime)
            
        if to_datetime:
            conditions.append("requested_at <= $2")
            params.append(to_datetime)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY processor ORDER BY processor"
        
        rows = await conn.fetch(query, *params)
        
        result = {}
        for processor in all_processors:
            result[processor] = {
                "totalRequests": 0,
                "totalAmount": Decimal('0.00')
            }
        
        for row in rows:
            result[row['processor']] = {
                "totalRequests": row['total_requests'],
                "totalAmount": Decimal(str(row['total_amount'])).quantize(Decimal('0.01')) if row['total_amount'] else Decimal('0.00')
            }
            
        return result

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def purge_payments() -> int:
    """
    Delete all records from the payments table.
    Returns the number of deleted records.
    """
    async with get_connection() as conn:
        result = await conn.execute('DELETE FROM payments')
        # Extract the number of affected rows from the result
        # The result format is typically "DELETE count"
        deleted_count = int(result.split()[-1]) if result else 0
        return deleted_count 