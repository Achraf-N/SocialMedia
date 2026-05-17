# Startup Guide

## Quick Start: Run Everything at Once

Choose one method based on your preference:

---

## Method 1: PowerShell (Recommended for Windows)

```powershell
# Run from project root
.\start_all.ps1
```

**What it does:**
- Opens 2 new PowerShell windows
- Starts Backend API (Port 8000)
- Starts LangGraph API (Port 5000)
- Keeps processes running separately

**Pros:**
- Easy to monitor each service
- Easy to restart individual services
- Color-coded output

---

## Method 2: Batch File (Windows)

```cmd
start_all.bat
```

**What it does:**
- Opens 2 new command windows
- Starts Backend API (Port 8000)
- Starts LangGraph API (Port 5000)

**Pros:**
- Simple, standard Windows approach
- Works on any Windows machine

---

## Method 3: Python Script (Cross-Platform)

```bash
python start_services.py
```

**What it does:**
- Runs both services in same terminal
- Shows live monitoring
- Auto-stops all services on Ctrl+C

**Pros:**
- Works on Windows, Mac, Linux
- Shows all output in one place
- Clean shutdown with Ctrl+C

---

## Method 4: Manual (Terminal Tabs)

If you prefer full control:

**Terminal 1:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2:**
```bash
cd langgraph
python -m app.api.server
```

---

## After Startup

### Check Services Are Running

```bash
# Backend
curl http://localhost:8000/health

# LangGraph
curl http://localhost:5000/health
```

Or open in browser:
- Backend: http://localhost:8000/health
- LangGraph: http://localhost:5000/health

### Test Chat

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What products do you have?",
    "session_id": "test_user",
    "shop_id": "6a09d431697b1d38b68a50ce"
  }'
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000
# or on Windows
netstat -ano | findstr :5000

# Kill process
kill -9 <PID>
```

### Services Don't Start
- ✓ Check Python is installed: `python --version`
- ✓ Check venv is activated: `(venv)` should appear in prompt
- ✓ Check dependencies: `pip install -r requirements.txt`
- ✓ Check MongoDB is running (for backend)

### Backend Error: MongoDB Connection
```
MongoServerSelectionTimeoutError
```
- Start MongoDB: `mongod`
- Or check `.env` has correct `MONGODB_URI`

### LangGraph Error: Ollama Connection
```
ConnectionError: localhost:11434
```
- Start Ollama: `ollama serve`
- Check model: `ollama list`

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Backend Health | http://localhost:8000/health | Check backend running |
| LangGraph Health | http://localhost:5000/health | Check API running |
| Chat Endpoint | POST http://localhost:5000/chat | Send chat messages |
| Config Endpoint | POST http://localhost:5000/config | Configure backend URL |

---

## Production Deployment

For production, use a process manager:

### Option 1: PM2 (Node.js)
```bash
npm install -g pm2

# Create pm2 config
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: './backend',
      script: 'uvicorn',
      args: 'app.main:app --port 8000 --host 0.0.0.0',
      env: { NODE_ENV: 'production' }
    },
    {
      name: 'langgraph',
      cwd: './langgraph',
      script: 'python',
      args: '-m app.api.server',
      env: { FLASK_ENV: 'production' }
    }
  ]
};
EOF

pm2 start ecosystem.config.js
```

### Option 2: Docker Compose
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017
    depends_on:
      - mongo
  
  langgraph:
    build: ./langgraph
    ports:
      - "5000:5000"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
  
  mongo:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

Then run:
```bash
docker-compose up
```

---

## Systemd Service (Linux)

Create `/etc/systemd/system/langgraph.service`:

```ini
[Unit]
Description=LangGraph Chatbot API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/langgraph
ExecStart=/usr/bin/python3 -m app.api.server
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl start langgraph
sudo systemctl enable langgraph
```
