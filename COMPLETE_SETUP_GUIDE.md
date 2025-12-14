# 🚀 Complete Setup Guide: Nevo AI Assistant

**A comprehensive, beginner-friendly guide to set up and run the Nevo AI Assistant locally**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding the Project Structure](#understanding-the-project-structure)
3. [Python Version Setup](#python-version-setup)
4. [Virtual Environment Setup](#virtual-environment-setup)
5. [Backend Setup](#backend-setup)
6. [Frontend Setup](#frontend-setup)
7. [Running the Application](#running-the-application)
8. [How It Works](#how-it-works)
9. [Troubleshooting](#troubleshooting)
10. [Quick Reference](#quick-reference)

---

## 📦 Prerequisites

Before you begin, make sure you have:

### **Required Software:**

1. **Python 3.11+** (see [Python Version Setup](#python-version-setup))
2. **Node.js 18+** and npm (for frontend)
3. **PostgreSQL** (for database - optional, can use SQLite for testing)
4. **Git** (to clone repositories)

### **Required Accounts:**

1. **OpenAI API Key** - Get from https://platform.openai.com/api-keys
   - ⚠️ **This is REQUIRED** - The application won't work without it

### **Optional Tools:**

- **pyenv** - For managing Python versions (recommended)
- **Pipenv** - For managing Python dependencies (recommended, or use venv)

---

## 🏗️ Understanding the Project Structure

### **What is This Project?**

The Nevo AI Assistant is a voice-enabled chatbot framework that can be customized for different use cases (like car sales, product recommendations, etc.).

### **Project Components:**

```
Nevo-Demo/
├── nevo-backend-framework-main/        # Core framework (shared code)
│   └── src/nevo_framework/            # Framework source code
│
├── nevo-audi-pitch-backend-main/      # Pitch version backend (sales-focused)
│   ├── src/
│   │   ├── main.py                    # Entry point
│   │   └── llm/
│   │       └── audi_orchestrator.py  # Business logic
│   ├── config/
│   │   └── master_config.json        # Configuration
│   └── .env                          # Environment variables
│
├── Nevo-Framwork-chat-bot/            # Shop version (browsing-focused)
│   ├── nevo-audi-shop-backend-main/   # Shop backend
│   └── nevo-audi-shop-frontend-main/ # Shop frontend
│
└── audi-nevo-frontend-main/           # Pitch version frontend
```

### **Key Concepts:**

- **Framework**: Shared code that handles WebSocket, audio processing, agent orchestration
- **Backend**: Your custom business logic (orchestrator, agents, RAG)
- **Frontend**: React application that users interact with
- **Orchestrator**: The "brain" that routes conversations to different agents

---

## 🐍 Python Version Setup

### **Why Python 3.11?**

Both the framework and backend require **Python 3.11 or higher**. Python 3.9 or 3.10 won't work.

### **Check Your Python Version:**

```bash
python3 --version
# Should show: Python 3.11.x or higher
```

### **Option 1: Using pyenv (Recommended)**

**Install pyenv** (if not installed):
```bash
# macOS
brew install pyenv

# Linux
curl https://pyenv.run | bash
```

**Install Python 3.11:**
```bash
# List available versions
pyenv install --list | grep 3.11

# Install Python 3.11.9 (or latest 3.11.x)
pyenv install 3.11.9
```

**Set Python version for your project:**
```bash
# For backend
cd nevo-audi-pitch-backend-main
pyenv local 3.11.9

# For framework
cd ../nevo-backend-framework-main
pyenv local 3.11.9
```

**Verify:**
```bash
python3 --version
# Should show: Python 3.11.9
```

### **Option 2: Using System Python**

If you already have Python 3.11+ installed:
```bash
# Check version
python3 --version

# If it's 3.11+, you're good to go!
```

### **Troubleshooting Python Version:**

**Problem**: "Python 3.11 not found"
```bash
# Install via pyenv
pyenv install 3.11.9
pyenv local 3.11.9
```

**Problem**: "Wrong Python version being used"
```bash
# Check which Python
which python3
python3 --version

# Set explicitly
pyenv local 3.11.9
```

---

## 🐍 Virtual Environment Setup

### **What is a Virtual Environment?**

A virtual environment is an isolated Python environment for your project. It prevents conflicts between different projects' dependencies.

### **Option 1: Using Pipenv (Recommended)**

Pipenv automatically creates and manages virtual environments.

**Install Pipenv:**
```bash
pip3 install pipenv
```

**For Framework:**
```bash
cd nevo-backend-framework-main

# Install framework in editable mode
pipenv install -e .
```

**For Backend:**
```bash
cd nevo-audi-pitch-backend-main

# Install all dependencies
pipenv install
```

**Activate Virtual Environment:**
```bash
pipenv shell
# Your prompt should change to show (project-name)
```

**Run Commands:**
```bash
# Run without activating shell
pipenv run python src/main.py

# Or activate first, then run
pipenv shell
python src/main.py
```

**Deactivate:**
```bash
exit  # Or close terminal
```

### **Option 2: Using Standard venv**

**Create Virtual Environment:**
```bash
cd nevo-audi-pitch-backend-main
python3 -m venv venv
# or
python3 -m venv .venv
```

**Activate:**
```bash
# macOS/Linux
source venv/bin/activate
# or
source .venv/bin/activate

# Windows
venv\Scripts\activate
```

**Install Dependencies:**
```bash
# If you have requirements.txt
pip install -r requirements.txt

# Or install pipenv and use it
pip install pipenv
pipenv install
```

**Deactivate:**
```bash
deactivate
```

### **Verify Virtual Environment:**

```bash
# Check if you're in a virtual environment
which python
# Should show path to venv/bin/python

# Or check
echo $VIRTUAL_ENV
# Should show path to virtual environment
```

### **Important Notes:**

- ✅ Virtual environments are **automatically ignored by git** (in `.gitignore`)
- ✅ Each project has its **own virtual environment**
- ✅ **Never commit** virtual environments to git
- ✅ **Do commit** `Pipfile` and `Pipfile.lock` (they define dependencies)

---

## ⚙️ Backend Setup

### **Step 1: Install Framework Dependencies**

```bash
cd nevo-backend-framework-main

# Make sure you're using Python 3.11
python3 --version

# Install pipenv if not installed
pip3 install pipenv

# Install framework in editable mode
pipenv install -e .
```

**What this does:**
- Creates a virtual environment
- Installs the framework as an editable package
- Makes framework available to your backend

**Expected output:**
```
Creating a virtualenv for this project...
Installing dependencies from Pipfile.lock...
✅ Successfully installed nevo-framework
```

### **Step 2: Install Backend Dependencies**

```bash
cd ../nevo-audi-pitch-backend-main

# Install all backend dependencies
pipenv install
```

**What this does:**
- Creates a virtual environment for backend
- Installs all required packages (FastAPI, OpenAI, etc.)

**Expected output:**
```
Installing dependencies from Pipfile.lock...
✅ Successfully installed fastapi uvicorn openai ...
```

### **Step 3: Create Backend .env File**

Create a `.env` file in the backend directory:

```bash
cd nevo-audi-pitch-backend-main

# Create .env file
cat > .env << 'EOF'
# OpenAI API Key (REQUIRED - Get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-proj-REPLACE_WITH_YOUR_ACTUAL_KEY

# Authentication (default password: test123)
HASHED_PASSWORD=$2b$12$hJOKAOiDvFGQFmOT6EYO7e2DP5/icdPGqydXRyp5SNeP93eu0LQdi

# JWT Secret (for session tokens)
JWT_SECRET_KEY=my-secret-key-for-local-development-only-minimum-32-characters

# Database (PostgreSQL - optional, can use SQLite for testing)
DATABASE_URL=postgresql://user:password@localhost:5432/nevo_db

# Salesforce (optional - leave empty if not using)
SALESFORCE_SANDBOX_USERNAME=
SALESFORCE_SANDBOX_PASSWORD=
SALESFORCE_SANDBOX_TOKEN=

# Optional settings
ENABLE_DOCS=false
PORT=8000
EOF
```

**⚠️ IMPORTANT:**
1. **Replace `REPLACE_WITH_YOUR_ACTUAL_KEY`** with your actual OpenAI API key
2. **Get your API key from:** https://platform.openai.com/api-keys
3. **Never commit `.env` files** - They contain secrets!

### **Step 4: Verify Configuration**

Check that the config points to your orchestrator:

```bash
cd nevo-audi-pitch-backend-main

# Check orchestrator class
cat config/master_config.json | grep orchestrator_class
# Should show: "orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"

# Verify orchestrator file exists
ls -la src/llm/audi_orchestrator.py
# Should show the file
```

### **Step 5: Test Backend Installation**

```bash
cd nevo-audi-pitch-backend-main

# Activate virtual environment
pipenv shell

# Test import
python -c "import nevo_framework; print('Framework imported successfully!')"

# If successful, you should see:
# Framework imported successfully!
```

---

## 🎨 Frontend Setup

### **Step 1: Install Node.js Dependencies**

```bash
cd audi-nevo-frontend-main

# Install dependencies
npm install

# If you get peer dependency warnings, use:
npm install --legacy-peer-deps
```

### **Step 2: Create Frontend .env File**

```bash
cd audi-nevo-frontend-main

# Create .env file
cat > .env << 'EOF'
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=local
EOF
```

**What these do:**
- `VITE_BACKEND_URL`: Where the frontend sends API requests
- `VITE_WEBSOCKET_URL`: WebSocket connection for real-time communication
- `VITE_ENVIRONMENT`: Environment mode (local/dev/prod)

---

## 🚀 Running the Application

### **Step 1: Start Backend**

**Terminal 1:**
```bash
cd nevo-audi-pitch-backend-main

# Activate virtual environment
pipenv shell

# Start backend server
python src/main.py
```

**Expected output:**
```
Loaded configuration from config/master_config.json
Orchestrator class llm.audi_orchestrator.AudiAgentOrchestrator validated successfully.
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**✅ Success indicators:**
- No error messages
- "Uvicorn running on http://0.0.0.0:8000"
- Orchestrator validated successfully

### **Step 2: Start Frontend**

**Terminal 2 (new terminal):**
```bash
cd audi-nevo-frontend-main

# Start development server
npm run dev
```

**Expected output:**
```
  VITE v5.4.1  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**✅ Success indicators:**
- No error messages
- Server running on http://localhost:5173

### **Step 3: Open in Browser**

1. **Open browser:** http://localhost:5173
2. **Login:**
   - Password: `test123`
3. **Test voice interaction:**
   - Click microphone button or hold spacebar
   - Say: "I need a car" or "Show me cars"
   - Watch for AI response

### **Step 4: Verify Everything Works**

**Check backend logs:**
```
<<<AI>>> Dialog step started
<<<AI>>> Orchestrator state: user_profile_state
<<<AI>>> Response: [AI's response text]
```

**Check frontend:**
- Login successful
- Microphone button works
- AI responds to voice input

---

## 🔍 How It Works

### **The Call Chain:**

```
1. User speaks into frontend
   ↓
2. Frontend sends audio via WebSocket
   ↓
3. Framework receives audio
   ↓
4. Framework converts audio to text (Speech-to-Text)
   ↓
5. Framework calls YOUR orchestrator
   ↓
6. Orchestrator routes to appropriate agent
   ↓
7. Agent processes request (uses RAG, LLM, etc.)
   ↓
8. Agent returns response
   ↓
9. Framework converts text to speech (Text-to-Speech)
   ↓
10. Framework sends audio back to frontend
   ↓
11. Frontend plays audio to user
```

### **Key Files:**

**Backend Entry Point (`src/main.py`):**
```python
from nevo_framework.api import api as framework_api

if __name__ == "__main__":
    framework_api.main()  # Starts FastAPI server
```

**Framework (`nevo_framework/api/api.py`):**
- Handles WebSocket connections
- Manages audio processing
- Routes to your orchestrator

**Your Orchestrator (`src/llm/audi_orchestrator.py`):**
- Your custom business logic
- Routes conversations to different agents
- Handles user profile, recommendations, test drives, etc.

**Config (`config/master_config.json`):**
```json
{
  "orchestrator_class": "llm.audi_orchestrator.AudiAgentOrchestrator"
}
```
This tells the framework which orchestrator to use.

### **Request Flow Diagram:**

```
Frontend (localhost:5173)
  │
  ├─► Login: POST http://localhost:8000/login
  │   Body: {"password": "test123"}
  │   Response: {"session_id": "...", "token": "..."}
  │
  └─► WebSocket: ws://localhost:8000/ws
      │
      ├─► Frontend sends: {"type": "audio", "data": "..."}
      │
      ├─► Framework receives via WebSocket
      │   (nevo_framework/api/api.py)
      │
      ├─► Framework creates DialogManager
      │   └─► Loads YOUR orchestrator from config
      │
      ├─► DialogManager calls orchestrator.dialog_step()
      │   └─► YOUR CODE runs (audi_orchestrator.py)
      │       └─► Calls your agents (UserProfile, Recommendation, etc.)
      │
      ├─► Framework sends response back
      │   Message: {"type": "show_image", "image": "..."}
      │
      └─► Frontend receives and displays
```

---

## 🐛 Troubleshooting

### **Backend Issues**

#### **"Module not found: nevo_framework"**

**Problem:** Framework not installed or not in path.

**Solution:**
```bash
cd nevo-backend-framework-main
pipenv install -e .

# Verify
python -c "import nevo_framework; print(nevo_framework.__file__)"
```

#### **"Orchestrator class not found"**

**Problem:** Config points to wrong path or file doesn't exist.

**Solution:**
```bash
# Check config
cat config/master_config.json | grep orchestrator_class

# Verify file exists
ls -la src/llm/audi_orchestrator.py

# If path is wrong, update master_config.json
```

#### **"OPENAI_API_KEY not found"**

**Problem:** `.env` file missing or key not set.

**Solution:**
```bash
# Check .env exists
ls -la .env

# Check key is set
cat .env | grep OPENAI_API_KEY

# Make sure you replaced REPLACE_WITH_YOUR_ACTUAL_KEY
```

#### **"Port 8000 already in use"**

**Problem:** Another process is using port 8000.

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in .env
echo "PORT=8001" >> .env
```

#### **"Python version mismatch"**

**Problem:** Wrong Python version being used.

**Solution:**
```bash
# Check version
python3 --version

# Set correct version
pyenv local 3.11.9

# Recreate virtual environment
pipenv --rm
pipenv install
```

### **Frontend Issues**

#### **"Cannot connect to backend"**

**Problem:** Backend not running or wrong URL.

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check .env file
cat .env | grep VITE_BACKEND_URL
# Should show: VITE_BACKEND_URL=http://localhost:8000

# Check browser console for CORS errors
```

#### **"npm install fails"**

**Problem:** Node.js version too old or dependency conflicts.

**Solution:**
```bash
# Check Node.js version
node --version
# Should be 18+

# Use legacy peer deps
npm install --legacy-peer-deps

# Or clear cache
rm -rf node_modules package-lock.json
npm install
```

#### **"WebSocket connection failed"**

**Problem:** Backend not running or WebSocket URL wrong.

**Solution:**
```bash
# Check backend is running
# Check .env has correct WebSocket URL
cat .env | grep VITE_WEBSOCKET_URL
# Should show: VITE_WEBSOCKET_URL=ws://localhost:8000/ws
```

### **Virtual Environment Issues**

#### **"pipenv: command not found"**

**Solution:**
```bash
pip3 install pipenv
```

#### **"Virtual environment not activating"**

**Solution:**
```bash
# Check if venv exists
pipenv --venv

# If not, create it
pipenv install

# Activate explicitly
pipenv shell
```

#### **"Module not found" errors**

**Solution:**
```bash
# Make sure you're in virtual environment
pipenv shell

# Reinstall dependencies
pipenv install

# Verify package is installed
pipenv graph | grep package-name
```

### **General Issues**

#### **"Permission denied" errors**

**Solution:**
```bash
# Make scripts executable
chmod +x script.sh

# Or use sudo (not recommended)
sudo command
```

#### **"Out of memory" errors**

**Solution:**
- Close other applications
- Reduce batch size in config
- Use smaller models

---

## 📚 Quick Reference

### **Common Commands**

```bash
# Activate virtual environment
pipenv shell

# Run backend
python src/main.py

# Run frontend
npm run dev

# Check Python version
python3 --version

# Check if in virtual environment
which python

# List installed packages
pipenv graph

# Recreate virtual environment
pipenv --rm
pipenv install
```

### **File Locations**

```
Backend .env:        nevo-audi-pitch-backend-main/.env
Frontend .env:       audi-nevo-frontend-main/.env
Config:              nevo-audi-pitch-backend-main/config/master_config.json
Orchestrator:        nevo-audi-pitch-backend-main/src/llm/audi_orchestrator.py
Framework:           nevo-backend-framework-main/src/nevo_framework/
```

### **Ports**

- **Backend:** 8000
- **Frontend:** 5173
- **WebSocket:** ws://localhost:8000/ws

### **Environment Variables**

**Backend (.env):**
- `OPENAI_API_KEY` - **REQUIRED** - Your OpenAI API key
- `HASHED_PASSWORD` - Optional - Login password hash (default: test123)
- `JWT_SECRET_KEY` - Optional - Session token signing
- `DATABASE_URL` - Optional - PostgreSQL connection string
- `PORT` - Optional - Backend port (default: 8000)

**Frontend (.env):**
- `VITE_BACKEND_URL` - **REQUIRED** - Backend API endpoint
- `VITE_WEBSOCKET_URL` - **REQUIRED** - WebSocket connection
- `VITE_ENVIRONMENT` - **REQUIRED** - Environment mode

### **Default Credentials**

- **Login Password:** `test123`
- **Backend Port:** `8000`
- **Frontend Port:** `5173`

---

## ✅ Checklist

Before running the application, make sure:

- [ ] Python 3.11+ installed and set
- [ ] Node.js 18+ installed
- [ ] Virtual environment created and activated
- [ ] Framework installed (`pipenv install -e .` in framework directory)
- [ ] Backend dependencies installed (`pipenv install` in backend directory)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Backend `.env` file created with `OPENAI_API_KEY`
- [ ] Frontend `.env` file created with correct URLs
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can login with password `test123`
- [ ] Voice interaction works

---

## 🎯 Next Steps

Once everything is working:

1. **Customize the orchestrator** - Edit `src/llm/audi_orchestrator.py`
2. **Add your RAG documents** - Place in `documents/` directory
3. **Configure agents** - Modify agent prompts and logic
4. **Add features** - User profiles, test drives, image walkarounds
5. **Deploy** - Set up for production

---

## 📖 Additional Resources

- **Framework Documentation:** `nevo-backend-framework-main/README.md`
- **Feature Implementation:** `Nevo-Framwork-chat-bot/nevo-audi-shop-backend-main/FEATURES_IMPLEMENTATION.md`
- **Image Walkaround Setup:** `Nevo-Framwork-chat-bot/nevo-audi-shop-backend-main/IMAGE_WALKAROUND_SETUP.md`

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs:**
   - Backend: Terminal where you ran `python src/main.py`
   - Frontend: Terminal where you ran `npm run dev`
   - Browser: Developer console (F12)

2. **Verify setup:**
   - Python version: `python3 --version`
   - Virtual environment: `which python`
   - Environment variables: `cat .env`

3. **Common fixes:**
   - Reinstall dependencies
   - Recreate virtual environment
   - Check file paths
   - Verify API keys

---

**🎉 You're all set! Happy coding!**

---

*Last updated: 2024*
*For questions or issues, refer to the troubleshooting section above.*

