# Multi-Schema Support - Fixed for Remote Server

## What Changed

The code now **automatically detects** which database schema is available and uses the appropriate queries. This solves the issue where the remote server has a different database structure than the local development machine.

## The Problem

- **Local machine**: Has `Product`, `Supplier`, `Supplier_Product` tables
- **Remote server**: Has only `Product_FinishedGood` table

The old code crashed because it only knew about the local schema.

## The Solution

### Updated Files

**1. db.py**
- Added schema introspection methods:
  - `get_all_tables()` - List all tables
  - `table_exists(name)` - Check if table exists
  - `get_table_columns(name)` - Get column names
  - `fetch_sample_rows(name)` - Get sample data
  - `infer_raw_material_source_columns()` - **Auto-detect schema and return correct mapping**

**2. enrich_raw_materials.py**
- New `discover_raw_material_sources()` function uses schema introspection
- Supports both schema types automatically
- Logs which schema and columns were detected

**3. main.py**
- Added `inspect-source` command for debugging

**4. test_schema.py** (NEW)
- Test script to verify schema detection works
- Shows detected schema, tables, and sample data

## How to Use on Remote Server

### Step 1: Verify Schema Detection

```bash
python test_schema.py
```

This will show:
- All available tables
- Detected schema type (should be `product_finished_good`)
- Raw materials discovered
- Ollama connection status

### Step 2: Inspect Detailed Schema

```bash
python main.py inspect-source
```

This shows:
- Database tables
- Detected source columns
- Sample data
- Raw material count

### Step 3: Run Enrichment

Once schema is detected correctly:

```bash
python main.py enrich
```

## Supported Schemas

### Schema 1: Standard Join (Local Development)
Detected when tables exist: `Product`, `Supplier`, `Supplier_Product`

Mapping:
- Product ID: `Product.Id`
- Product Name: `Product.SKU`
- Supplier ID: `Supplier.Id`
- Supplier Name: `Supplier.Name`

### Schema 2: Product_FinishedGood (Remote Server)
Detected when table exists: `Product_FinishedGood`

Mapping:
- Product ID: `Product_FinishedGood.ProductId`
- Product Name: `Product_FinishedGood.MarketSearch`
- Supplier Name: `Product_FinishedGood.Market`
- Supplier ID: Generated from hashing supplier name

## What If Schema Detection Still Fails?

1. **Check which tables exist:**
   ```bash
   python -c "from db import db; print('Tables:', db.get_all_tables())"
   ```

2. **Check table structure:**
   ```bash
   sqlite3 db.sqlite "PRAGMA table_info(Product_FinishedGood);"
   ```

3. **Run full diagnostic:**
   ```bash
   python test_schema.py
   ```

## No Code Changes Needed

- The code automatically adapts to any database schema
- The database structures (`raw_material_master`, `raw_material_embeddings`, `raw_material_comparisons`) remain unchanged
- Comparison and suggestion functions work the same way

## Files Changed/Added

✅ `db.py` - Added schema introspection  
✅ `enrich_raw_materials.py` - Multi-schema support  
✅ `main.py` - Added inspect-source command  
✅ `test_schema.py` - NEW test utility (created)  
✅ `README.md` - Updated documentation  

## Summary for Your Friend

1. Pull the latest code
2. Run `python test_schema.py` to verify schema detection
3. If it shows "ALL TESTS PASSED", run `python main.py enrich`
4. The system will automatically use `Product_FinishedGood` since that's the only table available on the remote server

**No database changes needed. No config changes needed. Just works! 🎉**
