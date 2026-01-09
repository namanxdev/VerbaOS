-- =============================================================================
-- Azure PostgreSQL Database Schema for Speech-to-Intent System
-- Enable pgvector extension first in Azure Portal:
--   Server Parameters -> azure.extensions -> Select 'vector' -> Save
-- =============================================================================

-- Enable pgvector extension (run this first)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- USERS TABLE
-- Stores both patients and caretakers in a single table
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(8) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('patient', 'caretaker')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =============================================================================
-- PATIENT-CARETAKER LINKS (Many-to-Many)
-- A patient can have multiple caretakers, a caretaker can have multiple patients
-- =============================================================================
CREATE TABLE IF NOT EXISTS patient_caretaker_links (
    patient_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caretaker_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    linked_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (patient_id, caretaker_id)
);

-- Indexes for efficient lookup from both directions
CREATE INDEX IF NOT EXISTS idx_links_patient ON patient_caretaker_links(patient_id);
CREATE INDEX IF NOT EXISTS idx_links_caretaker ON patient_caretaker_links(caretaker_id);

-- =============================================================================
-- NOTIFICATIONS TABLE
-- Stores patient requests sent to caretakers
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(8) PRIMARY KEY,
    patient_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intent VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    transcription TEXT DEFAULT '',
    timestamp TIMESTAMP DEFAULT NOW(),
    read BOOLEAN DEFAULT FALSE
);

-- Index for fetching patient's notifications
CREATE INDEX IF NOT EXISTS idx_notifications_patient ON notifications(patient_id);
-- Index for timestamp ordering
CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp DESC);

-- =============================================================================
-- NOTIFICATION RECIPIENTS (Many-to-Many)
-- Which caretakers should receive each notification
-- =============================================================================
CREATE TABLE IF NOT EXISTS notification_recipients (
    notification_id VARCHAR(8) NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    caretaker_id VARCHAR(8) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    read_at TIMESTAMP DEFAULT NULL,
    PRIMARY KEY (notification_id, caretaker_id)
);

-- Index for fetching caretaker's notifications
CREATE INDEX IF NOT EXISTS idx_recipients_caretaker ON notification_recipients(caretaker_id);

-- =============================================================================
-- INTENT EMBEDDINGS TABLE
-- Stores 768-dimensional HuBERT embeddings for intent classification
-- Uses pgvector for native cosine similarity search
-- =============================================================================
CREATE TABLE IF NOT EXISTS intent_embeddings (
    id SERIAL PRIMARY KEY,
    intent VARCHAR(50) NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for intent filtering
CREATE INDEX IF NOT EXISTS idx_embeddings_intent ON intent_embeddings(intent);

-- IVFFlat index for approximate nearest neighbor search with cosine similarity
-- Note: Run this AFTER inserting initial data (needs at least 100 rows for good performance)
-- For small datasets (<1000), you can skip this and use exact search
-- CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON intent_embeddings 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- =============================================================================
-- VISITOR COUNT TABLE
-- Simple counter for website visitors
-- =============================================================================
CREATE TABLE IF NOT EXISTS visitor_count (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Initialize visitor count
INSERT INTO visitor_count (id, count) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- View: Patient with their caretakers
CREATE OR REPLACE VIEW patient_caretakers_view AS
SELECT 
    p.id as patient_id,
    p.name as patient_name,
    c.id as caretaker_id,
    c.name as caretaker_name,
    pcl.linked_at
FROM users p
JOIN patient_caretaker_links pcl ON p.id = pcl.patient_id
JOIN users c ON c.id = pcl.caretaker_id
WHERE p.role = 'patient' AND c.role = 'caretaker';

-- View: Caretaker with their patients
CREATE OR REPLACE VIEW caretaker_patients_view AS
SELECT 
    c.id as caretaker_id,
    c.name as caretaker_name,
    p.id as patient_id,
    p.name as patient_name,
    pcl.linked_at
FROM users c
JOIN patient_caretaker_links pcl ON c.id = pcl.caretaker_id
JOIN users p ON p.id = pcl.patient_id
WHERE c.role = 'caretaker' AND p.role = 'patient';

-- View: Intent embedding statistics
CREATE OR REPLACE VIEW intent_stats_view AS
SELECT 
    intent,
    COUNT(*) as sample_count,
    MIN(created_at) as first_sample,
    MAX(created_at) as last_sample
FROM intent_embeddings
GROUP BY intent
ORDER BY sample_count DESC;
