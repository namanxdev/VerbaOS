"""
Migration script to transfer data from JSON files to Azure PostgreSQL.
Run this once after setting up the database to migrate existing data.

Usage:
    python migrate_to_postgres.py

Requires DATABASE_URL environment variable or individual DB settings in .env
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import asyncpg


# File paths
DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
EMBEDDINGS_FILE = Path(__file__).parent / "intent_embeddings.json"
VISITOR_FILE = Path(__file__).parent / "visitor_count.json"


def get_connection_string():
    """Build PostgreSQL connection string from environment."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    host = os.getenv("DATABASE_HOST", "")
    user = os.getenv("DATABASE_USER", "")
    password = os.getenv("DATABASE_PASSWORD", "")
    database = os.getenv("DATABASE_NAME", "postgres")
    port = os.getenv("DATABASE_PORT", "5432")
    ssl = os.getenv("DATABASE_SSL", "require")
    
    if not host or not user or not password:
        raise ValueError("Database connection settings not found. Set DATABASE_URL or individual settings in .env")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={ssl}"


async def migrate_users(conn):
    """Migrate users from JSON to PostgreSQL."""
    if not USERS_FILE.exists():
        print("[SKIP] users.json not found")
        return 0, 0
    
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
    
    users_migrated = 0
    links_migrated = 0
    
    # Migrate patients
    for user_id, user in data.get("patients", {}).items():
        try:
            created_at = datetime.fromisoformat(user["created_at"]) if user.get("created_at") else datetime.now()
            await conn.execute(
                """
                INSERT INTO users (id, name, role, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET name = $2
                """,
                user["id"], user["name"], "patient", created_at
            )
            users_migrated += 1
        except Exception as e:
            print(f"[ERROR] Failed to migrate patient {user_id}: {e}")
    
    # Migrate caretakers
    for user_id, user in data.get("caretakers", {}).items():
        try:
            created_at = datetime.fromisoformat(user["created_at"]) if user.get("created_at") else datetime.now()
            await conn.execute(
                """
                INSERT INTO users (id, name, role, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET name = $2
                """,
                user["id"], user["name"], "caretaker", created_at
            )
            users_migrated += 1
        except Exception as e:
            print(f"[ERROR] Failed to migrate caretaker {user_id}: {e}")
    
    # Migrate patient-caretaker links
    for patient_id, patient in data.get("patients", {}).items():
        for caretaker_id in patient.get("caretakers", []):
            try:
                await conn.execute(
                    """
                    INSERT INTO patient_caretaker_links (patient_id, caretaker_id, linked_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (patient_id, caretaker_id) DO NOTHING
                    """,
                    patient_id, caretaker_id, datetime.now()
                )
                links_migrated += 1
            except Exception as e:
                print(f"[ERROR] Failed to create link {patient_id} -> {caretaker_id}: {e}")
    
    return users_migrated, links_migrated


async def migrate_notifications(conn):
    """Migrate notifications from JSON to PostgreSQL."""
    if not NOTIFICATIONS_FILE.exists():
        print("[SKIP] notifications.json not found")
        return 0
    
    with open(NOTIFICATIONS_FILE, "r") as f:
        notifications = json.load(f)
    
    migrated = 0
    
    for notif in notifications:
        try:
            timestamp = datetime.fromisoformat(notif["timestamp"]) if notif.get("timestamp") else datetime.now()
            
            # Insert notification
            await conn.execute(
                """
                INSERT INTO notifications (id, patient_id, intent, message, confidence, transcription, timestamp, read)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                """,
                notif["id"],
                notif["patient_id"],
                notif["intent"],
                notif["message"],
                notif.get("confidence", 0.0),
                notif.get("transcription", ""),
                timestamp,
                notif.get("read", False)
            )
            
            # Link to caretakers
            for caretaker_id in notif.get("caretaker_ids", []):
                await conn.execute(
                    """
                    INSERT INTO notification_recipients (notification_id, caretaker_id)
                    VALUES ($1, $2)
                    ON CONFLICT (notification_id, caretaker_id) DO NOTHING
                    """,
                    notif["id"], caretaker_id
                )
            
            migrated += 1
        except Exception as e:
            print(f"[ERROR] Failed to migrate notification {notif.get('id')}: {e}")
    
    return migrated


async def migrate_embeddings(conn):
    """Migrate intent embeddings from JSON to PostgreSQL with pgvector."""
    if not EMBEDDINGS_FILE.exists():
        print("[SKIP] intent_embeddings.json not found")
        return 0
    
    with open(EMBEDDINGS_FILE, "r") as f:
        embeddings_data = json.load(f)
    
    migrated = 0
    
    for intent, embeddings in embeddings_data.items():
        for embedding in embeddings:
            try:
                # Convert to pgvector format
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await conn.execute(
                    """
                    INSERT INTO intent_embeddings (intent, embedding, created_at)
                    VALUES ($1, $2::vector, $3)
                    """,
                    intent, embedding_str, datetime.now()
                )
                migrated += 1
            except Exception as e:
                print(f"[ERROR] Failed to migrate embedding for {intent}: {e}")
    
    return migrated


async def migrate_visitor_count(conn):
    """Migrate visitor count from JSON to PostgreSQL."""
    if not VISITOR_FILE.exists():
        print("[SKIP] visitor_count.json not found")
        return 0
    
    with open(VISITOR_FILE, "r") as f:
        data = json.load(f)
    
    count = data.get("count", 0)
    
    try:
        await conn.execute(
            """
            INSERT INTO visitor_count (id, count, last_updated)
            VALUES (1, $1, $2)
            ON CONFLICT (id) DO UPDATE SET count = $1, last_updated = $2
            """,
            count, datetime.now()
        )
        return count
    except Exception as e:
        print(f"[ERROR] Failed to migrate visitor count: {e}")
        return 0


async def run_schema(conn):
    """Create database tables directly with Python."""
    print("[INFO] Creating tables...")
    
    # Step 1: Enable pgvector extension
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("[OK] pgvector extension enabled")
    except Exception as e:
        print(f"[WARNING] Extension: {e}")
    
    # Step 2: Create users table
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(8) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('patient', 'caretaker')),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("[OK] Created 'users' table")
    except Exception as e:
        print(f"[ERROR] users table: {e}")
    
    # Step 3: Create patient_caretaker_links table
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS patient_caretaker_links (
                patient_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                caretaker_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                linked_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (patient_id, caretaker_id)
            )
        """)
        print("[OK] Created 'patient_caretaker_links' table")
    except Exception as e:
        print(f"[ERROR] patient_caretaker_links table: {e}")
    
    # Step 4: Create notifications table
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id VARCHAR(8) PRIMARY KEY,
                patient_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                intent VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                transcription TEXT DEFAULT '',
                timestamp TIMESTAMP DEFAULT NOW(),
                read BOOLEAN DEFAULT FALSE
            )
        """)
        print("[OK] Created 'notifications' table")
    except Exception as e:
        print(f"[ERROR] notifications table: {e}")
    
    # Step 5: Create notification_recipients table
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_recipients (
                notification_id VARCHAR(8) NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
                caretaker_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                read_at TIMESTAMP DEFAULT NULL,
                PRIMARY KEY (notification_id, caretaker_id)
            )
        """)
        print("[OK] Created 'notification_recipients' table")
    except Exception as e:
        print(f"[ERROR] notification_recipients table: {e}")
    
    # Step 6: Create intent_embeddings table with pgvector
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS intent_embeddings (
                id SERIAL PRIMARY KEY,
                intent VARCHAR(50) NOT NULL,
                embedding vector(768) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("[OK] Created 'intent_embeddings' table (with vector)")
    except Exception as e:
        print(f"[ERROR] intent_embeddings table: {e}")
    
    # Step 7: Create visitor_count table
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS visitor_count (
                id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            INSERT INTO visitor_count (id, count) VALUES (1, 0) ON CONFLICT (id) DO NOTHING
        """)
        print("[OK] Created 'visitor_count' table")
    except Exception as e:
        print(f"[ERROR] visitor_count table: {e}")
    
    # Step 8: Create indexes
    try:
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_intent ON intent_embeddings(intent)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_patient ON notifications(patient_id)")
        print("[OK] Created indexes")
    except Exception as e:
        print(f"[WARNING] Indexes: {e}")
    
    print("[OK] Schema creation finished")
    return True


async def main():
    """Main migration function."""
    print("=" * 60)
    print("Azure PostgreSQL Migration Script")
    print("=" * 60)
    
    try:
        conn_string = get_connection_string()
        print(f"[INFO] Connecting to database...")
        
        conn = await asyncpg.connect(conn_string)
        print("[OK] Connected to PostgreSQL")
        
        # Run schema
        print("\n[STEP 1] Creating schema...")
        await run_schema(conn)
        
        # Migrate users
        print("\n[STEP 2] Migrating users...")
        users, links = await migrate_users(conn)
        print(f"[OK] Migrated {users} users and {links} patient-caretaker links")
        
        # Migrate notifications
        print("\n[STEP 3] Migrating notifications...")
        notifs = await migrate_notifications(conn)
        print(f"[OK] Migrated {notifs} notifications")
        
        # Migrate embeddings
        print("\n[STEP 4] Migrating intent embeddings...")
        embeddings = await migrate_embeddings(conn)
        print(f"[OK] Migrated {embeddings} embeddings")
        
        # Migrate visitor count
        print("\n[STEP 5] Migrating visitor count...")
        count = await migrate_visitor_count(conn)
        print(f"[OK] Visitor count set to {count}")
        
        # Show stats
        print("\n" + "=" * 60)
        print("Migration Complete! Database Statistics:")
        print("=" * 60)
        
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        patient_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role = 'patient'")
        caretaker_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role = 'caretaker'")
        link_count = await conn.fetchval("SELECT COUNT(*) FROM patient_caretaker_links")
        notif_count = await conn.fetchval("SELECT COUNT(*) FROM notifications")
        embedding_count = await conn.fetchval("SELECT COUNT(*) FROM intent_embeddings")
        
        print(f"  Users:        {user_count} ({patient_count} patients, {caretaker_count} caretakers)")
        print(f"  Links:        {link_count}")
        print(f"  Notifications: {notif_count}")
        print(f"  Embeddings:   {embedding_count}")
        
        # Show embedding stats per intent
        print("\n  Embeddings by Intent:")
        rows = await conn.fetch("SELECT intent, COUNT(*) as count FROM intent_embeddings GROUP BY intent ORDER BY count DESC")
        for row in rows:
            print(f"    {row['intent']}: {row['count']}")
        
        await conn.close()
        print("\n[OK] Migration completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
