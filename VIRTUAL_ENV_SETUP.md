# 🐍 Python Virtual Environment Setup Guide

## Quick Start: Using Virtual Environments

This project uses **Pipenv** for dependency management. Here's how to set up and use virtual environments:

### **Option 1: Using Pipenv (Recommended)**

Pipenv automatically creates and manages virtual environments for you.

#### **For Backend Framework:**
```bash
cd nevo-backend-framework-main
pipenv install -e .  # Installs framework in editable mode
```

#### **For Your Backend:**
```bash
cd nevo-audi-pitch-backend-main
pipenv install  # Installs all dependencies from Pipfile
```

#### **Activate Virtual Environment:**
```bash
pipenv shell  # Activates the virtual environment
```

#### **Run Commands in Virtual Environment:**
```bash
pipenv run python src/main.py  # Runs without activating shell
```

#### **Deactivate:**
```bash
exit  # Or just close the terminal
```

---

### **Option 2: Using Standard venv**

If you prefer standard Python venv:

#### **Create Virtual Environment:**
```bash
cd nevo-audi-pitch-backend-main
python3 -m venv venv
# or
python3 -m venv .venv
```

#### **Activate Virtual Environment:**

**On macOS/Linux:**
```bash
source venv/bin/activate
# or
source .venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
# or
.venv\Scripts\activate
```

#### **Install Dependencies:**
```bash
pip install -r requirements.txt  # If you have requirements.txt
# or install from Pipfile
pip install pipenv
pipenv install --dev
```

#### **Deactivate:**
```bash
deactivate
```

---

## 📁 Virtual Environment Locations

With the `.gitignore` file at the root, these directories are ignored:

- `venv/` - Standard virtual environment
- `.venv/` - Alternative virtual environment name
- `env/` - Another common name
- `.pipenv/` - Pipenv's virtual environment location

**All virtual environments are automatically ignored by git!** ✅

---

## 🔍 Check Your Virtual Environment

### **Check if you're in a virtual environment:**
```bash
which python
# Should show path to venv/bin/python or similar

# Or check:
echo $VIRTUAL_ENV
```

### **List installed packages:**
```bash
pip list
# or with pipenv:
pipenv graph
```

---

## 🚀 Recommended Workflow

1. **Install Pipenv globally** (if not already installed):
   ```bash
   pip3 install pipenv
   ```

2. **Navigate to your project:**
   ```bash
   cd nevo-audi-pitch-backend-main
   ```

3. **Install dependencies:**
   ```bash
   pipenv install
   ```

4. **Activate virtual environment:**
   ```bash
   pipenv shell
   ```

5. **Run your application:**
   ```bash
   python src/main.py
   ```

6. **When done, exit:**
   ```bash
   exit
   ```

---

## ⚠️ Important Notes

1. **Never commit virtual environments** - They're already in `.gitignore` ✅
2. **Commit Pipfile and Pipfile.lock** - These define your dependencies
3. **Each project can have its own virtual environment** - Framework and backend are separate
4. **Virtual environments are project-specific** - Don't share them between projects

---

## 🐛 Troubleshooting

### **"pipenv: command not found"**
```bash
pip3 install pipenv
```

### **"Module not found" errors**
Make sure you're in the virtual environment:
```bash
pipenv shell
# Then try again
```

### **Virtual environment not activating**
Check if it exists:
```bash
pipenv --venv  # Shows path to virtual environment
```

### **Want to recreate virtual environment?**
```bash
pipenv --rm  # Remove existing
pipenv install  # Create new one
```

---

## 📝 Summary

- ✅ `.gitignore` is set up at root - all virtual environments are ignored
- ✅ Use `pipenv` for automatic virtual environment management
- ✅ Activate with `pipenv shell` before running Python code
- ✅ Each backend project has its own virtual environment

**Your virtual environments are safe from git!** 🎉

