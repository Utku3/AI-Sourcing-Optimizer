# Python Version Compatibility Guide

## Python Version Requirements

Your friends are using **Python 3.11**, which is actually **fully compatible** with this codebase. However, let me explain what could go wrong and how to fix it.

---

## Current Code Status with Python 3.11

### ✅ What Works Fine

The code uses modern Python 3.9+ syntax:
- Type hints like `list[str]` (PEP 585) ✓
- Type hints like `Dict[str, Any]` from typing ✓
- f-strings with variables ✓
- Context managers with `with` statements ✓
- All standard library features used ✓

Python 3.11 fully supports all of this.

---

## Potential Issues on Python 3.11

### Issue 1: NumPy/SciPy Compatibility on ROCm

If they're running on AMD ROCm server with **ROCm drivers**, NumPy might have architecture-specific wheels that don't work.

**Symptom:**
```
ImportError: cannot import name '...' from 'numpy'
ModuleNotFoundError: No module named 'numpy'
```

**Fix:**
```bash
# On ROCm server, explicitly install ROCm-compatible wheels
pip install --upgrade rocm-libs

# Or use CPU-only version if ROCm fails
pip install numpy --no-cache-dir --force-reinstall
```

---

### Issue 2: sentence-transformers Installation

sentence-transformers can be slow to install on Python 3.11 if wheels aren't available.

**Symptom:**
```
error: Microsoft Visual C++ 14.0 or greater is required
Installation failed (on Windows)
```

**Fix:**
```bash
# Install with binary wheels (recommended)
pip install sentence-transformers --only-binary=:all:

# Or pre-install torch separately
pip install torch
pip install sentence-transformers
```

---

### Issue 3: SQLite3 on Different OSes

SQLite3 behavior is slightly different on:
- Windows with Python 3.11
- Linux with Python 3.11  
- macOS with Python 3.11

**Symptom:**
```
sqlite3.OperationalError: database is locked
sqlite3.DatabaseError: file is encrypted or is not a database
```

**Fix:**
```bash
# Delete WAL files if database is corrupted
rm db.sqlite-wal db.sqlite-shm

# Rebuild database
python main.py setup
```

---

### Issue 4: Requests Library Timeout on ROCm

On a remote AMD server, HTTP timeouts might occur with Ollama.

**Symptom:**
```
requests.exceptions.ConnectionError: Connection aborted
Timeout waiting for response from http://localhost:11434
```

**Fix:** Increase timeout in `config.py`:
```python
OLLAMA_TIMEOUT_SECONDS: int = 300  # Increase from 120 to 300 seconds
```

---

## Step-by-Step Setup for Python 3.11

Your friend should follow this order:

### Step 1: Verify Python Version

```bash
python --version
```

Should output: `Python 3.11.x` (where x is any number)

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows
```

### Step 3: Upgrade pip, setuptools, wheel

```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies with Verbose Output

```bash
pip install -r requirements.txt -v
```

If this fails, install manually:

```bash
pip install requests
pip install sentence-transformers
pip install openai
```

### Step 5: Test Imports

```bash
python -c "import sqlite3; import requests; import json; print('✓ All imports OK')"
```

### Step 6: Test Database

```bash
python main.py setup
python main.py inspect-source
```

---

## Troubleshooting by Error Type

### Error: "ModuleNotFoundError: No module named 'requests'"

**Solution:**
```bash
pip install requests --upgrade
```

### Error: "failed to import sentence_transformers"

**Solution:**
```bash
pip install torch  # Install base dependency first
pip install sentence-transformers
```

### Error: "sqlite3.OperationalError: attempted to write a readonly database"

**Solution:**
```bash
# Database file permissions issue
# Check file permissions
ls -la db.sqlite

# Fix permissions (Linux/Mac)
chmod 644 db.sqlite
```

### Error: "ConnectionError: cannot connect to http://localhost:11434"

**Solution:**
```bash
# Verify Ollama is running
ollama list

# If not running, start it
ollama serve  # In separate terminal
```

### Error: "timeout waiting for response"

**Solution:** Update config.py:
```python
OLLAMA_TIMEOUT_SECONDS = 300  # Increase from 120
```

---

## Environment-Specific Setup

### On Windows with Python 3.11

```bash
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py setup
```

### On Linux AMD ROCm with Python 3.11

```bash
# Load ROCm modules first (if using module system)
module load rocm

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install with ROCm support
pip install --upgrade pip
pip install rocm-libs  # Install base ROCm libraries
pip install -r requirements.txt

python main.py setup
```

### On macOS with Python 3.11

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py setup
```

---

## What Works Perfectly on Python 3.11

✅ Database operations (sqlite3)  
✅ HTTP requests (requests library)  
✅ Type hints (PEP 585/604 syntax)  
✅ JSON encoding/decoding  
✅ File I/O  
✅ Logging  
✅ Argparse CLI  
✅ Context managers  

---

## Quick Version Compatibility Checklist

For your friend to verify Python 3.11 compatibility:

```bash
# 1. Check Python version
python --version

# 2. Check pip version (should be 21.0+)
pip --version

# 3. Test core imports
python -c "
import sys
import sqlite3
import requests
import json
print(f'Python: {sys.version}')
print(f'sqlite3: OK')
print(f'requests: OK')
print(f'✓ All core modules available')
"

# 4. Test code imports
python -c "from db import db; from ollama_client import client; print('✓ Code imports OK')"

# 5. Test database
python main.py setup
python main.py inspect-source

# 6. Run test schema
python test_schema.py
```

---

## Summary: Python 3.11 Compatibility

**Your friend's Python 3.11 is compatible!**

The most likely issues are:
1. **Missing dependencies** → `pip install -r requirements.txt`
2. **Ollama not running** → `ollama serve` in separate terminal
3. **Database locked** → Delete `.sqlite-wal` files
4. **Timeout issues** → Increase `OLLAMA_TIMEOUT_SECONDS` in config.py
5. **ROCm conflicts** → `pip install rocm-libs` before other packages

**Tell your friend to:**
1. Run: `python --version` (should be 3.11.x)
2. Run: `pip install -r requirements.txt`
3. Run: `python main.py setup`
4. Run: `python main.py inspect-source`

If steps 2-4 work, Python 3.11 setup is complete!
