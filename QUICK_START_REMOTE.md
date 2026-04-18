# IMMEDIATE ACTION CHECKLIST FOR FRIEND

## 🚀 Quick Start - Remote Server Setup

Copy-paste these commands in order on the remote server:

### Step 1: Pull Latest Code (Has All Fixes)
```bash
git pull origin ibo
```

### Step 2: Verify Everything Works
```bash
python verify_setup.py
```

**Expected Output:** ✓ ALL CHECKS PASSED

### Step 3A: Load Test Data (If No Production Data)
```bash
python setup_test_database.py remote
```

### Step 3B: Or Load Production Data
```bash
# If you have production database, import it:
# (Ask me if you need help with this step)
```

### Step 4: Run Enrichment
```bash
python main.py enrich
```

**Expected:** "Discovered X raw materials" (X > 0)

---

## ✅ Test Each Command

Once enrichment completes, test **all 4 core commands**:

### Test 1: Schema Inspection
```bash
python main.py inspect-source
```
**Should show:**
- Detection Method: product_finished_good
- Total raw materials to enrich: X
- **No warnings or errors**

### Test 2: Compare Products
```bash
python main.py compare 1 1 2 1
```
**Should show:** Comparison scores (no "no such table" error)

### Test 3: Get Suggestions
```bash
python main.py suggest 1
```
**Should show:** List of alternatives (no "no such table" error)

### Test 4: Test Schema Script
```bash
python test_schema.py
```
**Should show:** ✓ ALL TESTS PASSED

---

## 🔧 If Something Fails

### Issue: "no such table: Product"
✓ **FIXED** - Pull latest code: `git pull origin ibo`

### Issue: "KeyError: product_type_col"
✓ **FIXED** - Pull latest code: `git pull origin ibo`

### Issue: Discovered 0 raw materials
→ Need to load data into `Product_FinishedGood` table
→ Use: `python setup_test_database.py remote`

### Issue: Ollama timeout
→ Edit `config.py`:
```python
OLLAMA_TIMEOUT_SECONDS = 300  # was 120
```
→ Then retry

### Issue: Import error with ollama_client
→ Correct syntax is:
```python
from ollama_client import ollama_client  # NOT "client"
```

---

## 📋 Status Check Commands

**Quick health check:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tables:', [t[0] for t in cur.fetchall()])
cur.execute('SELECT COUNT(*) FROM Product_FinishedGood')
print('Product_FinishedGood rows:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM raw_material_master')
print('raw_material_master rows:', cur.fetchone()[0])
"
```

**Check Ollama:**
```bash
ollama list
ollama ps  # shows running models
```

---

## 🎯 Success Criteria

After following all steps, you should have:

- [ ] `git pull` succeeded
- [ ] `verify_setup.py` shows ✓ ALL CHECKS PASSED
- [ ] `Product_FinishedGood` has rows (> 0)
- [ ] `raw_material_master` has rows after enrichment
- [ ] `main.py inspect-source` runs without errors
- [ ] `main.py compare 1 1 2 1` returns scores
- [ ] `main.py suggest 1` returns alternatives
- [ ] `test_schema.py` shows ✓ ALL TESTS PASSED

If all ✓, **YOU'RE DONE!** System is working!

---

## 🆘 Need Help?

If something still doesn't work:

1. Run and save output of: `python verify_setup.py`
2. Run and save output of: `python test_schema.py`
3. Run and save output of: `python main.py inspect-source`
4. Send me these outputs

---

## 📞 Summary

**Fixed Issues:**
- ✅ Schema key errors
- ✅ "no such table: Product" crashes  
- ✅ Schema detection for Product_FinishedGood
- ✅ Graceful fallbacks for missing tables

**Your job:**
1. Pull code
2. Load data (test or production)
3. Run enrich
4. Test commands

**Done!**
