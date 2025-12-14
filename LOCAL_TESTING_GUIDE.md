# 🚀 LOCAL TESTING GUIDE: audi-nevo-frontend-main + nevo-audi-pitch-backend-main

## 📋 HOW THE FRAMEWORK IS CALLED - EXPLAINED

### **The Call Chain:**

```
1. python src/main.py
   ↓
2. main.py loads .env → imports nevo_framework
   ↓
3. Calls framework_api.main()
   ↓
4. Framework starts FastAPI server (uvicorn)
   ↓
5. Framework reads config/master_config.json
   ↓
6. Framework loads YOUR orchestrator class: "llm.audi_orchestrator.AudiAgentOrchestrator"
   ↓
7. Framework handles WebSocket connections and routes to YOUR orchestrator
```

### **Key Files:**

**Your Backend (main.py):**
```python
from pathlib import Path
import sys
from dotenv import load_dotenv

def _ensure_framework_on_path() -> None:
    # Adds framework to Python path if not installed
    framework_dir = (
        Path(__file__).resolve().parents[2]  # workspace root
        / "nevo-backend-framework-main" / "src"
    )
    if framework_dir.exists() and str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))

_ensure_framework_on_path()
load_dotenv()  # Loads OPENAI_API_KEY from .env

from nevo_framework.api import api as framework_api

if __name__ == "__main__":
    framework_api.main()  # Start FastAPI server
```

**Framework (api.py):**
```python
def main():
    validate_orchestrator_class()  # Checks your orchestrator exists
    uvicorn.run(app, host="0.0.0.0", port=port, ...)  # Starts server
```

**Config (master_config.json):**
```json
"orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
```
This tells framework to use `audi_orchestrator.py`

---

## ⚙️ SETUP STEPS

### **Step 1: Install Framework Dependencies**

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-backend-framework-main

# Install pipenv if not installed
pip3 install pipenv

# Install framework as editable package
pipenv install -e .
```

### **Step 2: Install Backend Dependencies**

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-audi-pitch-backend-main

# Install backend dependencies (Pipfile has been updated with all required packages)
pipenv install
```

**✅ Fixed:** Your Pipfile now includes all required packages:
- `python-dotenv`, `beautifulsoup4`, `requests`, `pydantic`, `pillow`
- `fastapi`, `uvicorn`, `websockets`, `aiofiles`, `aiohttp`
- `openai`, `pandas`, `bcrypt`, `pyjwt`, and more

### **Step 3: Create Backend .env File**

Create `/Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-audi-pitch-backend-main/.env`:

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-audi-pitch-backend-main

cat > .env << 'EOF'
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-proj-REPLACE_WITH_YOUR_ACTUAL_KEY

# Authentication (default password: test123)
HASHED_PASSWORD=$2b$12$hJOKAOiDvFGQFmOT6EYO7e2DP5/icdPGqydXRyp5SNeP93eu0LQdi

# JWT Secret
JWT_SECRET_KEY=my-secret-key-for-local-development-only-minimum-32-characters

# Salesforce (optional - leave empty if not using)
SALESFORCE_SANDBOX_USERNAME=
SALESFORCE_SANDBOX_PASSWORD=
SALESFORCE_SANDBOX_TOKEN=

# Optional settings
ENABLE_DOCS=false
EOF
```

**⚠️ IMPORTANT:** Replace `REPLACE_WITH_YOUR_ACTUAL_KEY` with your actual OpenAI API key from https://platform.openai.com/api-keys

### **Step 4: Create Frontend .env File**

Create `/Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/audi-nevo-frontend-main/.env`:

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/audi-nevo-frontend-main

cat > .env << 'EOF'
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=local
EOF
```

**✅ Fixed:** Frontend constants.ts now uses port 8000 (was 8080)

### **Step 5: Verify Configuration**

Check that `master_config.json` points to your orchestrator:

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-audi-pitch-backend-main
cat config/master_config.json | grep orchestrator_class
# Should show: "orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
```

**✅ Fixed:** `recording_file_dir` is now set to `"temp"` (directory created)

### **Step 6: Start Backend**

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/nevo-audi-pitch-backend-main

# Activate pipenv shell
pipenv shell

# Run the backend
python src/main.py
```

**Expected output:**
```
Loaded configuration from config/master_config.json
Orchestrator class llm.audi_orchestrator.AudiAgentOrchestrator validated successfully.
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### **Step 7: Start Frontend (in new terminal)**

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/audi-nevo-frontend-main

# Install Node.js dependencies (if not already done)
npm install

# Start development server
npm run dev
```

**Expected output:**
```
  VITE v5.4.1  ready in 500 ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## ✅ TESTING

### **Step 8: Test the Application**

1. **Open Browser:**
   ```
   http://localhost:5173
   ```

2. **Login:**
   - Password: `test123`

3. **Test Voice Interaction:**
   - Click microphone or hold spacebar
   - Say: "I need a car"
   - Watch backend logs for AI response

4. **Check Backend Logs:**
   ```
   <<<AI>>> Dialog step started
   <<<AI>>> Orchestrator state: user_profile_state
   <<<AI>>> Response: [AI's response text]
   ```

---

## 🔍 HOW IT WORKS - DETAILED FLOW

### **Request Flow:**

```
1. Frontend (localhost:5173)
   │
   ├─► Login: POST http://localhost:8000/login
   │   Body: {"password": "test123"}
   │   Response: {"session_id": "...", "token": "..."}
   │
   └─► WebSocket: ws://localhost:8000/ws
       │
       ├─► Frontend sends audio/text
       │   Message: {"type": "audio", "data": "..."}
       │
       ├─► Framework receives via WebSocket
       │   (/nevo_framework/api/api.py)
       │
       ├─► Framework creates DialogManager
       │   └─► Loads YOUR orchestrator from config
       │       "llm.audi_orchestrator.AudiAgentOrchestrator"
       │
       ├─► DialogManager calls orchestrator.chat_step()
       │   └─► YOUR CODE in /src/llm/audi_orchestrator.py runs
       │       └─► Calls your agents (UserProfile, Recommendation, etc.)
       │
       ├─► Framework sends response back to frontend
       │   Message: {"type": "show_image", "image": "..."}
       │
       └─► Frontend receives and displays in 3D showroom
```

### **Key Framework Entry Points:**

1. **api.py** - `main()` starts server
2. **api.py** - WebSocket handler (`/ws/audio/{session_id}`)
3. **dialog_manager.py** - Routes to your orchestrator
4. **YOUR audi_orchestrator.py** - Your business logic

---

## 🐛 TROUBLESHOOTING

### **Backend won't start:**

```bash
# Check if framework is found
python -c "import nevo_framework; print(nevo_framework.__file__)"

# If not found, install it:
cd ../nevo-backend-framework-main
pipenv install -e .
```

### **"Module not found" errors:**

```bash
# Update Pipfile with all packages (already done)
cd nevo-audi-pitch-backend-main
pipenv install
```

### **"Orchestrator class not found":**

Check that master_config.json points to correct path:
```json
"orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
```

Verify the file exists:
```bash
ls -la src/llm/audi_orchestrator.py
```

### **Frontend can't connect:**

- Check backend is running on port 8000
- Check .env has correct URLs:
  ```bash
  cat .env | grep VITE_BACKEND_URL
  # Should show: VITE_BACKEND_URL=http://localhost:8000
  ```
- Check browser console for CORS errors
- Verify backend logs show: `Uvicorn running on http://0.0.0.0:8000`

### **"OPENAI_API_KEY not found":**

```bash
# Verify .env file exists and has the key
cd nevo-audi-pitch-backend-main
cat .env | grep OPENAI_API_KEY

# Make sure you replaced REPLACE_WITH_YOUR_ACTUAL_KEY with your real key
```

---

## 📝 ENVIRONMENT VARIABLES REFERENCE

### **BACKEND (.env)**

| Variable | Status | Default | Purpose |
|----------|--------|---------|---------|
| `OPENAI_API_KEY` | **REQUIRED** | None | OpenAI API access - **MUST SET!** |
| `HASHED_PASSWORD` | Optional | "test123" | Login password hash |
| `JWT_SECRET_KEY` | Optional | Auto-generated | Session token signing |
| `SALESFORCE_*` | Optional | None | Only if using Salesforce integration |
| `AZURE_OPENAI_API_KEY` | Optional | None | Only if using Azure OpenAI |
| `API_BASE` | Optional | None | Azure OpenAI endpoint |
| `PORT` | Optional | 8000 | Backend server port |
| `ENABLE_DOCS` | Optional | false | Enable API docs at /docs |

### **FRONTEND (.env)**

| Variable | Status | Purpose |
|----------|--------|---------|
| `VITE_BACKEND_URL` | **REQUIRED** | Backend API endpoint |
| `VITE_WEBSOCKET_URL` | **REQUIRED** | WebSocket connection |
| `VITE_ENVIRONMENT` | **REQUIRED** | Env mode (local/dev/prod) |

---

## 📁 DIRECTORY STRUCTURE

```
/Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/
├── nevo-backend-framework-main/     # Framework (shared)
│   └── src/nevo_framework/          # Framework source
│
├── nevo-audi-pitch-backend-main/    # Your backend
│   ├── src/
│   │   ├── main.py                  # ✅ Fixed: Calls framework with path setup
│   │   └── llm/
│   │       └── audi_orchestrator.py # Your orchestrator
│   ├── config/
│   │   └── master_config.json       # ✅ Fixed: Points to your orchestrator
│   ├── .env                         # ⚠️ Create this (see Step 3)
│   ├── Pipfile                      # ✅ Fixed: All dependencies added
│   └── temp/                        # ✅ Created: For audio recordings
│
└── audi-nevo-frontend-main/         # Your frontend
    ├── src/
    │   ├── constants/constants.ts   # ✅ Fixed: Port 8000
    │   └── AIShowroom.tsx           # 3D UI
    └── .env                         # ⚠️ Create this (see Step 4)
```

---

## 🎯 QUICK START SUMMARY

```bash
# 1. Get your OpenAI API Key from: https://platform.openai.com/api-keys

# 2. Install framework
cd nevo-backend-framework-main
pipenv install -e .

# 3. Install backend dependencies
cd ../nevo-audi-pitch-backend-main
pipenv install

# 4. Create backend .env with your OpenAI key
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE" > .env
echo "HASHED_PASSWORD=\$2b\$12\$hJOKAOiDvFGQFmOT6EYO7e2DP5/icdPGqydXRyp5SNeP93eu0LQdi" >> .env

# 5. Create frontend .env
cd ../audi-nevo-frontend-main
cat > .env << 'EOF'
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=local
EOF

# 6. Start backend
cd ../nevo-audi-pitch-backend-main
pipenv shell
python src/main.py

# 7. Start frontend (in new terminal)
cd ../audi-nevo-frontend-main
npm run dev

# 8. Open browser: http://localhost:5173
#    Login with password: test123
```

---

## 🚨 IMPORTANT NOTES

1. **Never commit .env files to git** - They contain secrets!
2. **OPENAI_API_KEY is the ONLY required variable** - Everything else has defaults
3. **Default login password is "test123"** - Change HASHED_PASSWORD to use different password
4. **Salesforce variables are optional** - Only needed if your orchestrator uses Salesforce
5. **Port 8000** - Both frontend and backend now use port 8000 ✅

---

## ✅ CHANGES MADE

1. ✅ **main.py** - Added `_ensure_framework_on_path()` function to handle framework import
2. ✅ **Pipfile** - Added all required dependencies (fastapi, uvicorn, openai, etc.)
3. ✅ **constants.ts** - Changed port from 8080 to 8000
4. ✅ **master_config.json** - Fixed `recording_file_dir` path to `"temp"`
5. ✅ **temp/** - Created directory for audio recordings
6. ✅ **.env files** - Instructions provided (files are git-ignored)

---

**Ready to test!** Follow the steps above and let me know if you hit any issues! 🚀

