# Azure PostgreSQL Setup Guide 🗄️

Step-by-step guide to set up Azure Database for PostgreSQL with pgvector for the Speech-to-Intent system.

---

## 📋 Prerequisites & Pre-Creation Checklist

### BEFORE You Click Create:
1. **Check Your Region**: Ensure you select the same region as your other services (like Azure ML) to minimize latency and avoid data transfer costs.
   - *Tip: East US is usually the cheapest and most feature-rich.*
2. **Verify Credits**: Go to [portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/overview](https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/overview) to check your remaining credit balance.
3. **Resource Group Plan**: Decide if you want a new Resource Group (cleaner for hackathons) or an existing one. We recommend a dedicated one (e.g., `hackathon-db-rg`) so you can delete everything easily later.
4. **Password Strategy**: Write down your admin username and password *before* creating. Resetting it later takes time.

### Tools Needed:
- Azure account with $100 credits (or active subscription)
- Azure CLI installed (optional, for command-line setup)

---

## 🚀 Step 1: Create PostgreSQL Server in Azure Portal

### 1.1 Navigate to Azure Portal
1. Go to [portal.azure.com](https://portal.azure.com)
2. Sign in with your Microsoft account

### 1.2 Create Resource
1. Click **"+ Create a resource"** (top left)
2. Search for **"Azure Database for PostgreSQL Flexible Server"**
3. Click **Create**

### 1.3 Configure Basics
| Setting | Value |
|---------|-------|
| **Subscription** | Your subscription |
| **Resource group** | Create new: `speech-intent-rg` |
| **Server name** | `speech-intent-db` (must be globally unique) |
| **Region** | Same as your Azure ML (e.g., East US) |
| **PostgreSQL version** | 16 (latest) |
| **Workload type** | Development |

### 1.4 Compute + Storage (IMPORTANT - Cost Control!)
1. Click **"Configure server"**
2. Select:
   - **Compute tier**: `Burstable`
   - **Compute size**: `Standard_B1ms` (1 vCore, 2 GiB RAM)
   - **Storage**: `32 GiB` (minimum)
3. **Verify Price**: Look at the **"Estimated cost per month"** summary box in the configuration panel. It should show approx **$12-13 USD**.
   - *Note: If you see a higher price ($100+), you likely have "General Purpose" or "Memory Optimized" selected. Switch to "Burstable".*
   - *Note: Costs vary slightly by Region.*

### 1.5 Authentication
| Setting | Value |
|---------|-------|
| **Authentication method** | PostgreSQL authentication only |
| **Admin username** | `adminuser` (remember this!) |
| **Password** | Create a strong password (remember this!) |

### 1.6 Networking
1. Select **"Public access (allowed IP addresses)"**
2. Check ✅ **"Allow public access from any Azure service"**
3. Click **"+ Add current client IP address"** (allows your computer to connect)

### 1.7 Review + Create
1. Click **"Review + create"**
2. Review settings
3. Click **"Create"**
4. ⏳ Wait 5-10 minutes for deployment

---

## 🔧 Step 2: Enable pgvector Extension

### 2.1 Go to Server Parameters
1. After deployment completes, go to your PostgreSQL resource
2. In left sidebar, click **"Server parameters"**

### 2.2 Enable Vector Extension
1. Search for `azure.extensions`
2. In the dropdown, select **`VECTOR`**
3. Click **"Save"** at the top
4. ⏳ Wait 2-3 minutes for server to apply changes

![Enable pgvector](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/media/concepts-extensions/azure-extensions.png)

---

## 🔗 Step 3: Get Connection Details

### 3.1 Find Connection String
1. Go to your PostgreSQL resource
2. In left sidebar, click **"Connect"**
3. Note down:
   - **Server name**: `speech-intent-db.postgres.database.azure.com`
   - **Admin username**: `adminuser`
   - **Port**: `5432`

### 3.2 Update Your .env File
Add these lines to `Backend/.env`:

```env
# Azure PostgreSQL Database
DATABASE_HOST=speech-intent-db.postgres.database.azure.com
DATABASE_NAME=postgres
DATABASE_USER=adminuser
DATABASE_PASSWORD=your_password_here
DATABASE_PORT=5432
DATABASE_SSL=require
```

**OR** use a single connection URL:

```env
DATABASE_URL=postgresql://adminuser:your_password_here@speech-intent-db.postgres.database.azure.com:5432/postgres?sslmode=require
```

---

## 📦 Step 4: Install Python Dependencies

```bash
cd Backend
pip install asyncpg pgvector
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

---

## 🗃️ Step 5: Run Database Migration

### 5.1 Test Connection First
```bash
# Optional: Test with psql if installed
psql "host=speech-intent-db.postgres.database.azure.com dbname=postgres user=adminuser password=YOUR_PASSWORD sslmode=require"
```

### 5.2 Run Migration Script
```bash
cd Backend
python migrate_to_postgres.py
```

**Expected Output:**
```
============================================================
Azure PostgreSQL Migration Script
============================================================
[INFO] Connecting to database...
[OK] Connected to PostgreSQL
[STEP 1] Creating schema...
[OK] Schema created/updated
[STEP 2] Migrating users...
[OK] Migrated 11 users and 9 patient-caretaker links
[STEP 3] Migrating notifications...
[OK] Migrated 0 notifications
[STEP 4] Migrating intent embeddings...
[OK] Migrated 150 embeddings
[STEP 5] Migrating visitor count...
[OK] Visitor count set to 4

============================================================
Migration Complete! Database Statistics:
============================================================
  Users:        11 (7 patients, 4 caretakers)
  Links:        9
  Notifications: 0
  Embeddings:   150

  Embeddings by Intent:
    WATER: 30
    HELP: 25
    ...

[OK] Migration completed successfully!
```

---

## ✅ Step 6: Start Backend with Database

```bash
cd Backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**You should see:**
```
[INFO] Initializing PostgreSQL database connection...
[OK] Database connected
[INFO] Using PostgreSQL database for user management
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 🧪 Step 7: Verify Database is Working

### Check API Health
```bash
curl http://127.0.0.1:8000/api/health
```

### Check Users from Database
```bash
curl http://127.0.0.1:8000/api/users/
```

### Check Intent Stats
```bash
curl http://127.0.0.1:8000/api/db-stats
```

---

## 🔍 Troubleshooting

### Error: "connection refused"
- Check firewall rules in Azure Portal → Networking
- Add your IP address to allowed list

### Error: "password authentication failed"
- Double-check username and password in .env
- Username format should NOT include `@servername`

### Error: "extension vector does not exist"
- Go back to Server Parameters
- Make sure `VECTOR` is selected in `azure.extensions`
- Save and wait for restart

### Error: "SSL required"
- Make sure `DATABASE_SSL=require` is set
- Or add `?sslmode=require` to DATABASE_URL

---

## 💰 Cost Management

| Resource | Monthly Cost |
|----------|--------------|
| PostgreSQL B1ms | ~$12.41 |
| Storage (32GB) | ~$3.68 |
| **Total** | **~$16/month** |

**With $100 credits**: ~6 months of usage

### To Stop Costs When Not Using:
1. Go to your PostgreSQL resource
2. Click **"Stop"** (you can restart later)
3. Stopped servers don't incur compute costs (only storage)

---

## 📊 Database Schema Overview

```
┌─────────────────────┐     ┌─────────────────────────┐
│       users         │     │  patient_caretaker_links│
├─────────────────────┤     ├─────────────────────────┤
│ id (PK)             │◄───┐│ patient_id (FK)         │
│ name                │    └│ caretaker_id (FK)       │
│ role                │     │ linked_at               │
│ created_at          │     └─────────────────────────┘
└─────────────────────┘

┌─────────────────────┐     ┌─────────────────────────┐
│    notifications    │     │ notification_recipients │
├─────────────────────┤     ├─────────────────────────┤
│ id (PK)             │◄────│ notification_id (FK)    │
│ patient_id (FK)     │     │ caretaker_id (FK)       │
│ intent              │     │ read_at                 │
│ message             │     └─────────────────────────┘
│ confidence          │
│ timestamp           │
└─────────────────────┘

┌─────────────────────┐
│  intent_embeddings  │  ← pgvector for similarity search
├─────────────────────┤
│ id (PK)             │
│ intent              │
│ embedding vector(768)│  ← 768-dimensional HuBERT embeddings
│ created_at          │
└─────────────────────┘
```

---

## 🔄 Switching Back to JSON (if needed)

If you need to run without database (e.g., for local testing):

1. Remove or comment out database settings in `.env`:
```env
# DATABASE_HOST=...
# DATABASE_URL=...
```

2. Restart backend - it will automatically use JSON files

---

## 📚 Additional Resources

- [Azure PostgreSQL Documentation](https://learn.microsoft.com/en-us/azure/postgresql/)
- [pgvector Extension Guide](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-use-pgvector)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

---

## ✨ Quick Reference - .env Template

```env
# Azure ML - HuBERT (Primary)
REST_END_POINT__HUBERT=https://your-hubert-endpoint.azureml.net/score
PRIMARY_KEY__HUBERT=your_hubert_api_key

# Azure ML - Wav2Vec (Fallback)  
REST_END_POINT__WAVE2VEC=https://your-wav2vec-endpoint.azureml.net/score
PRIMARY_KEY__WAVE2VEC=your_wav2vec_api_key

# Azure PostgreSQL Database
DATABASE_HOST=speech-intent-db.postgres.database.azure.com
DATABASE_NAME=postgres
DATABASE_USER=adminuser
DATABASE_PASSWORD=YourStrongPassword123!
DATABASE_PORT=5432
DATABASE_SSL=require

# Server Config
HOST=127.0.0.1
PORT=8000
DEBUG=false
```
