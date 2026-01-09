"""
PostgreSQL Database Service with pgvector for Azure PostgreSQL.
Provides async database operations for users, notifications, and intent embeddings.
"""

import asyncpg
from asyncpg import Pool
from typing import Optional, List, Tuple
from datetime import datetime
import json
from contextlib import asynccontextmanager

from app.config import settings


class PostgresDB:
    """
    Async PostgreSQL database service with connection pooling.
    Uses pgvector for 768-dimensional embedding storage and cosine similarity search.
    """
    
    _instance: Optional['PostgresDB'] = None
    _pool: Optional[Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls) -> 'PostgresDB':
        """Initialize the database connection pool."""
        instance = cls()
        if instance._pool is None:
            # Build connection string
            if settings.DATABASE_URL:
                dsn = settings.DATABASE_URL
            else:
                dsn = f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
                if settings.DATABASE_SSL:
                    dsn += f"?sslmode={settings.DATABASE_SSL}"
            
            instance._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            print(f"[INFO] PostgreSQL connection pool initialized")
            
            # Register pgvector type
            async with instance._pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                # Register vector type codec
                await conn.set_type_codec(
                    'vector',
                    encoder=lambda v: v,
                    decoder=lambda v: v,
                    schema='public',
                    format='text'
                )
        return instance
    
    @classmethod
    async def close(cls):
        """Close the connection pool."""
        if cls._instance and cls._instance._pool:
            await cls._instance._pool.close()
            cls._instance._pool = None
            print("[INFO] PostgreSQL connection pool closed")
    
    @property
    def pool(self) -> Pool:
        if self._pool is None:
            raise RuntimeError("Database not initialized. Call PostgresDB.initialize() first.")
        return self._pool
    
    # =========================================================================
    # USER OPERATIONS
    # =========================================================================
    
    async def create_user(self, user_id: str, name: str, role: str) -> dict:
        """Create a new user (patient or caretaker)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, name, role, created_at)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, name, role, datetime.now()
            )
            return {
                "id": user_id,
                "name": name,
                "role": role,
                "created_at": datetime.now().isoformat()
            }
    
    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID with their linked patients/caretakers."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, role, created_at FROM users WHERE id = $1",
                user_id
            )
            if not row:
                return None
            
            user = {
                "id": row["id"],
                "name": row["name"],
                "role": row["role"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            
            # Get linked users based on role
            if row["role"] == "patient":
                caretakers = await conn.fetch(
                    """
                    SELECT caretaker_id FROM patient_caretaker_links 
                    WHERE patient_id = $1
                    """,
                    user_id
                )
                user["caretakers"] = [r["caretaker_id"] for r in caretakers]
                user["patients"] = None
            else:
                patients = await conn.fetch(
                    """
                    SELECT patient_id FROM patient_caretaker_links 
                    WHERE caretaker_id = $1
                    """,
                    user_id
                )
                user["patients"] = [r["patient_id"] for r in patients]
                user["caretakers"] = None
            
            return user
    
    async def list_users(self, role: Optional[str] = None) -> List[dict]:
        """List all users, optionally filtered by role."""
        async with self.pool.acquire() as conn:
            if role:
                rows = await conn.fetch(
                    "SELECT id, name, role, created_at FROM users WHERE role = $1",
                    role
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, name, role, created_at FROM users"
                )
            
            users = []
            for row in rows:
                user = await self.get_user(row["id"])
                if user:
                    users.append(user)
            return users
    
    async def link_patient_caretaker(self, patient_id: str, caretaker_id: str) -> bool:
        """Link a caretaker to a patient."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO patient_caretaker_links (patient_id, caretaker_id, linked_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (patient_id, caretaker_id) DO NOTHING
                    """,
                    patient_id, caretaker_id, datetime.now()
                )
                return True
            except Exception as e:
                print(f"[ERROR] Failed to link patient-caretaker: {e}")
                return False
    
    async def unlink_patient_caretaker(self, patient_id: str, caretaker_id: str) -> bool:
        """Unlink a caretaker from a patient."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM patient_caretaker_links 
                WHERE patient_id = $1 AND caretaker_id = $2
                """,
                patient_id, caretaker_id
            )
            return "DELETE" in result
    
    async def get_patient_caretakers(self, patient_id: str) -> List[dict]:
        """Get all caretakers for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id, u.name, u.role, u.created_at
                FROM users u
                JOIN patient_caretaker_links pcl ON u.id = pcl.caretaker_id
                WHERE pcl.patient_id = $1
                """,
                patient_id
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "role": r["role"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                }
                for r in rows
            ]
    
    async def get_caretaker_patients(self, caretaker_id: str) -> List[dict]:
        """Get all patients for a caretaker."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id, u.name, u.role, u.created_at
                FROM users u
                JOIN patient_caretaker_links pcl ON u.id = pcl.patient_id
                WHERE pcl.caretaker_id = $1
                """,
                caretaker_id
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "role": r["role"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                }
                for r in rows
            ]
    
    # =========================================================================
    # NOTIFICATION OPERATIONS
    # =========================================================================
    
    async def create_notification(
        self,
        notif_id: str,
        patient_id: str,
        intent: str,
        message: str,
        confidence: float = 0.0,
        transcription: str = "",
        caretaker_ids: List[str] = None
    ) -> dict:
        """Create a notification and link to caretakers."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                timestamp = datetime.now()
                
                # Insert notification
                await conn.execute(
                    """
                    INSERT INTO notifications (id, patient_id, intent, message, confidence, transcription, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    notif_id, patient_id, intent, message, confidence, transcription, timestamp
                )
                
                # Link to caretakers
                if caretaker_ids:
                    for cid in caretaker_ids:
                        await conn.execute(
                            """
                            INSERT INTO notification_recipients (notification_id, caretaker_id)
                            VALUES ($1, $2)
                            """,
                            notif_id, cid
                        )
                
                # Get patient name
                patient = await conn.fetchrow(
                    "SELECT name FROM users WHERE id = $1", patient_id
                )
                
                return {
                    "id": notif_id,
                    "patient_id": patient_id,
                    "patient_name": patient["name"] if patient else "Unknown",
                    "intent": intent,
                    "message": message,
                    "confidence": confidence,
                    "transcription": transcription,
                    "timestamp": timestamp.isoformat(),
                    "read": False,
                    "caretaker_ids": caretaker_ids or []
                }
    
    async def get_caretaker_notifications(
        self,
        caretaker_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> Tuple[List[dict], int, int]:
        """Get notifications for a caretaker. Returns (notifications, total, unread)."""
        async with self.pool.acquire() as conn:
            # Base query
            query = """
                SELECT n.id, n.patient_id, u.name as patient_name, n.intent, 
                       n.message, n.confidence, n.transcription, n.timestamp, 
                       nr.read_at IS NOT NULL as read
                FROM notifications n
                JOIN notification_recipients nr ON n.id = nr.notification_id
                JOIN users u ON n.patient_id = u.id
                WHERE nr.caretaker_id = $1
            """
            
            if unread_only:
                query += " AND nr.read_at IS NULL"
            
            query += " ORDER BY n.timestamp DESC LIMIT $2"
            
            rows = await conn.fetch(query, caretaker_id, limit)
            
            notifications = [
                {
                    "id": r["id"],
                    "patient_id": r["patient_id"],
                    "patient_name": r["patient_name"],
                    "intent": r["intent"],
                    "message": r["message"],
                    "confidence": r["confidence"],
                    "transcription": r["transcription"],
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                    "read": r["read"]
                }
                for r in rows
            ]
            
            # Get counts
            total = await conn.fetchval(
                """
                SELECT COUNT(*) FROM notification_recipients WHERE caretaker_id = $1
                """,
                caretaker_id
            )
            
            unread = await conn.fetchval(
                """
                SELECT COUNT(*) FROM notification_recipients 
                WHERE caretaker_id = $1 AND read_at IS NULL
                """,
                caretaker_id
            )
            
            return notifications, total, unread
    
    async def mark_notification_read(self, notification_id: str, caretaker_id: str) -> bool:
        """Mark a notification as read by a caretaker."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE notification_recipients 
                SET read_at = $1
                WHERE notification_id = $2 AND caretaker_id = $3
                """,
                datetime.now(), notification_id, caretaker_id
            )
            return "UPDATE" in result
    
    async def get_patient_notifications(self, patient_id: str, limit: int = 20) -> List[dict]:
        """Get notification history for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, patient_id, intent, message, confidence, 
                       transcription, timestamp, read
                FROM notifications
                WHERE patient_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
                """,
                patient_id, limit
            )
            
            return [
                {
                    "id": r["id"],
                    "patient_id": r["patient_id"],
                    "intent": r["intent"],
                    "message": r["message"],
                    "confidence": r["confidence"],
                    "transcription": r["transcription"],
                    "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                    "read": r["read"]
                }
                for r in rows
            ]
    
    # =========================================================================
    # INTENT EMBEDDINGS OPERATIONS (with pgvector)
    # =========================================================================
    
    async def add_embedding(self, intent: str, embedding: List[float]) -> bool:
        """Add an embedding to the database."""
        async with self.pool.acquire() as conn:
            try:
                # Convert embedding to pgvector format
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await conn.execute(
                    """
                    INSERT INTO intent_embeddings (intent, embedding, created_at)
                    VALUES ($1, $2::vector, $3)
                    """,
                    intent, embedding_str, datetime.now()
                )
                return True
            except Exception as e:
                print(f"[ERROR] Failed to add embedding: {e}")
                return False
    
    async def add_embeddings_batch(self, intent: str, embeddings: List[List[float]]) -> int:
        """Add multiple embeddings at once."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                count = 0
                for embedding in embeddings:
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    await conn.execute(
                        """
                        INSERT INTO intent_embeddings (intent, embedding, created_at)
                        VALUES ($1, $2::vector, $3)
                        """,
                        intent, embedding_str, datetime.now()
                    )
                    count += 1
                return count
    
    async def find_similar_intents(
        self,
        embedding: List[float],
        k: int = 5
    ) -> List[Tuple[str, float, int]]:
        """
        Find most similar intents using pgvector cosine similarity.
        Returns list of (intent, similarity, embedding_id) tuples.
        """
        async with self.pool.acquire() as conn:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            rows = await conn.fetch(
                """
                SELECT id, intent, 1 - (embedding <=> $1::vector) AS similarity
                FROM intent_embeddings
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                embedding_str, k
            )
            
            return [
                (r["intent"], float(r["similarity"]), r["id"])
                for r in rows
            ]
    
    async def get_intent_stats(self) -> dict:
        """Get count of embeddings per intent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT intent, COUNT(*) as count
                FROM intent_embeddings
                GROUP BY intent
                ORDER BY count DESC
                """
            )
            return {r["intent"]: r["count"] for r in rows}
    
    async def get_intent_embeddings(self, intent: str) -> List[List[float]]:
        """Get all embeddings for a specific intent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT embedding::text FROM intent_embeddings WHERE intent = $1
                """,
                intent
            )
            
            embeddings = []
            for row in rows:
                # Parse pgvector format: [x,y,z,...] -> list of floats
                vec_str = row["embedding"]
                vec_str = vec_str.strip("[]")
                if vec_str:
                    embeddings.append([float(x) for x in vec_str.split(",")])
            return embeddings
    
    async def clear_intent_embeddings(self, intent: str) -> int:
        """Clear all embeddings for an intent."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM intent_embeddings WHERE intent = $1",
                intent
            )
            # Extract count from "DELETE N"
            count = int(result.split()[-1]) if result else 0
            return count
    
    # =========================================================================
    # VISITOR COUNT OPERATIONS
    # =========================================================================
    
    async def increment_visitor_count(self) -> int:
        """Increment and return the visitor count."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE visitor_count SET count = count + 1, last_updated = $1
                WHERE id = 1
                RETURNING count
                """,
                datetime.now()
            )
            return row["count"] if row else 0
    
    async def get_visitor_count(self) -> int:
        """Get current visitor count."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT count FROM visitor_count WHERE id = 1"
            )
            return row["count"] if row else 0


# Global database instance (initialized on startup)
db: Optional[PostgresDB] = None


async def get_db() -> PostgresDB:
    """Get the database instance. Call initialize() first."""
    global db
    if db is None:
        db = await PostgresDB.initialize()
    return db


async def init_db():
    """Initialize database on application startup."""
    global db
    db = await PostgresDB.initialize()
    return db


async def close_db():
    """Close database on application shutdown."""
    await PostgresDB.close()
