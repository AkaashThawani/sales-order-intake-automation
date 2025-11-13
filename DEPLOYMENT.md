# 🚀 Deployment Guide

This guide covers deploying the Sales Order Automation backend to **Render** or **Railway** using Docker.

## 📋 Prerequisites

Before deploying, ensure you have:

1. **GitHub Repository**: Push your code to GitHub
2. **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Email Account**: Gmail or other SMTP/IMAP provider for email processing
4. **Render Account**: Sign up at [render.com](https://render.com)
5. **Railway Account**: Sign up at [railway.app](https://railway.app)

## 🔧 Pre-Deployment Setup

### 1. Environment Variables

Create a `.env` file locally and note these values for deployment:

```bash
# Required
GEMINI_API_KEY=your_google_gemini_api_key
EMAIL_ACCOUNT=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Optional (defaults provided)
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com
```

### 2. Test Locally with Docker

```bash
# Build and test locally
docker build -t sales-order-api .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key sales-order-api

# Or use docker-compose
docker-compose up --build
```

### 3. Push to GitHub

```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

---

## 🐳 Render Deployment (Recommended)

### Step 1: Create PostgreSQL Database

1. Go to [render.com](https://render.com) and sign in
2. Click **"New"** → **"PostgreSQL"**
3. Configure your database:
   - **Name**: `sales-order-db`
   - **Database**: `sales_orders`
   - **User**: `sales_user`
   - Choose your plan (Starter $7/month is sufficient)

4. **Wait for database creation** (2-3 minutes)
5. **Note the connection details** - you'll need the **Internal Database URL**

### Step 2: Create Web Service

1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure service:

| Setting | Value |
|---------|-------|
| **Name** | `sales-order-api` |
| **Runtime** | `Docker` |
| **Branch** | `main` |
| **Root Directory** | `./sales-order-intake-automation` (if in monorepo) |
| **Build Command** | (leave default) |
| **Start Command** | (leave default) |

### Step 3: Environment Variables

Add these in Render's Environment section:

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `postgresql://user:password@host:port/database` | From PostgreSQL service |
| `GEMINI_API_KEY` | Your Gemini API key | Required |
| `ENVIRONMENT` | `production` | |
| `DEBUG` | `false` | |
| `LOG_LEVEL` | `INFO` | |
| `PORT` | `8000` | |
| `PYTHONUNBUFFERED` | `1` | |
| `IMAP_SERVER` | `imap.gmail.com` | |
| `SMTP_SERVER` | `smtp.gmail.com` | |
| `EMAIL_ACCOUNT` | Your email | |
| `EMAIL_PASSWORD` | Your app password | |
| `SECRET_KEY` | `your-secret-key-change-in-production` | |
| `ALLOWED_ORIGINS` | `https://your-frontend.onrender.com` | |

### Step 4: Deploy

1. Click **"Create Web Service"**
2. **Wait for build and deployment** (5-10 minutes)
3. **Check the Health Check** passes at `/health`
4. **Note the service URL** (e.g., `https://sales-order-api.onrender.com`)

### Step 5: Database Migration

The app will automatically create tables on first run, but you can verify:

```bash
# Check if tables were created
curl https://your-api-url.onrender.com/health
```

---

## 📊 Database Storage on Render

### **How Data Persistence Works:**

1. **Local Development**: Uses SQLite (`sales_orders.db`)
2. **Render Production**: Uses **managed PostgreSQL**

### **Database Migration:**

The app automatically handles schema creation:

```python
# In models.py - creates tables on startup
create_tables()
```

### **Data Flow:**
```
User Email → AI Processing → PostgreSQL Database
                    ↓
Frontend → API → PostgreSQL ← Background Tasks
```

### **Backup & Reliability:**
- **Automatic Backups**: Render provides daily backups
- **High Availability**: PostgreSQL with automatic failover
- **Data Persistence**: Survives container restarts
- **Connection Pooling**: Built into SQLAlchemy

---

## 🧪 Testing Database Connection

After deployment, test the database:

```bash
# Test health (includes DB check)
curl https://your-api-url.onrender.com/health

# Test API docs
open https://your-api-url.onrender.com/docs

# Test creating an order
curl -X POST "https://your-api-url.onrender.com/api/process-email" \
  -H "Content-Type: application/json" \
  -d '{"email_content": "Hi, I need 5 coffee mugs", "order_id": null}'
```

---

## 🔄 Post-Deployment Configuration

### 1. Update Frontend

Update your React app's API base URL:

```typescript
// In src/lib/api.ts
const API_BASE_URL = 'https://your-deployed-api-url';
```

### 2. CORS Configuration

Add your frontend URL to `ALLOWED_ORIGINS`:

- **Render**: `https://your-frontend.onrender.com`
- **Railway**: `https://your-frontend.up.railway.app`

### 3. Email Setup (Optional)

For automated email processing:

1. Set up Gmail app password or use SMTP provider
2. Configure IMAP/SMTP settings in environment variables
3. Test email sending via API

---

## 🐛 Troubleshooting

### Build Failures

**Issue**: `pip install` fails
```
# Check requirements.txt for incompatible versions
# Update to compatible package versions
```

**Issue**: System dependencies missing
```
# Add missing packages to Dockerfile RUN command
RUN apt-get install -y package-name
```

### Runtime Errors

**Issue**: Database connection fails
```
# Check DATABASE_URL format
# For Railway: Use the provided DATABASE_URL
# For Render: Check PostgreSQL connection string
```

**Issue**: Health check fails
```
# Check logs: curl https://your-url.onrender.com/health
# Verify GEMINI_API_KEY is set correctly
```

**Issue**: CORS errors
```
# Update ALLOWED_ORIGINS with your frontend URL
# Include protocol (https://)
```

### Performance Issues

**Issue**: Slow startup
```
# Use Python 3.11+ in Dockerfile
# Enable Docker layer caching
```

**Issue**: Memory usage high
```
# Use slim Python image
# Configure Gunicorn workers if needed
```

---

## 📊 Monitoring & Maintenance

### Logs
- **Render**: View in service dashboard
- **Railway**: Check deployment logs

### Health Checks
```bash
# Monitor health endpoint
curl https://your-api-url/health
```

### Updates
```bash
# Push changes to GitHub
git push origin main

# Automatic deployment on both platforms
```

---

## 💰 Cost Comparison

| Platform | Free Tier | Paid Plan | Notes |
|----------|-----------|-----------|-------|
| **Render** | 750hrs/month | $7+/month | Generous free tier |
| **Railway** | $5/month credit | $5+/month | Simple pricing |

Both platforms offer:
- Automatic SSL certificates
- PostgreSQL databases
- Docker support
- Global CDN
- Automatic scaling

---

## 🎯 Next Steps

1. **Deploy Frontend**: Deploy React app to Vercel/Netlify
2. **Domain Setup**: Add custom domain
3. **Monitoring**: Set up error tracking (Sentry)
4. **Backup**: Configure database backups
5. **Scaling**: Add Redis for session management

## 📞 Support

- **Render Docs**: https://docs.render.com/
- **Railway Docs**: https://docs.railway.app/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

*Last Updated: 2025-11-12*
