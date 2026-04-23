## Schema Refactoring Summary

### Problem Fixed
The enrichment pipeline was hardcoded to assume the existence of `Product`, `Supplier`, and `Supplier_Product` tables, which caused `no such table: Product` errors when the schema wasn't available.

### Solution Implemented

#### 1. Added Schema Introspection Functions to `db.py`

**New Methods:**
- `get_all_tables()` - Returns list of all tables in the database
- `table_exists(table_name: str)` - Checks if a specific table exists
- `get_table_columns(table_name: str)` - Gets column names using PRAGMA table_info()
- `fetch_sample_rows(table_name: str, limit: int)` - Fetches sample rows with column names
- `infer_raw_material_source_columns()` - Dynamically discovers the mapping of columns to logical concepts (product_id, product_name, supplier_id, supplier_name)

#### 2. Updated `enrich_raw_materials.py`

**New Function:**
- `discover_raw_material_sources()` - Uses schema introspection to find raw materials
  - Calls `db.infer_raw_material_source_columns()` to get the column mapping
  - Dynamically builds SQL queries based on discovered schema
  - Logs which columns were used
  - Handles missing or renamed columns gracefully

**Changes:**
- Replaced hardcoded `db.get_raw_materials_with_suppliers()` call
- Now uses discovered column mappings
- Provides detailed logging of source columns used

#### 3. Added `inspect-source` Command to `main.py`

**New Function:**
- `inspect_source_command()` - Displays complete database schema information
  - Lists all tables in the database
  - Shows source data schema with column mappings
  - Displays sample rows from source table
  - Shows count of raw materials to be enriched
  - Provides 3 example raw materials

**New Subparser:**
- `python main.py inspect-source` discovers and displays:
  - Database tables
  - Source table schema detection
  - Product_FinishedGood schema (if exists)
  - Sample rows
  - Raw material data count

### Detected Schema

The system successfully detected:

- **Source Table**: Product
- **Product ID Column**: Id
- **Product Name Column**: SKU
- **Product Type Column**: Type (filter: raw-material)
- **Supplier ID Column**: Id (from Supplier table)
- **Supplier Name Column**: Name (from Supplier table)
- **Join Table**: Supplier_Product
- **Supplier Table**: Supplier

### Results

- **Total raw materials discovered**: 1633
- **Example materials**:
  1. RM-C2-soy-lecithin-cc38c49d (ID: 182) from ADM (Supplier ID: 1)
  2. RM-C5-medium-chain-triglycerides-mct-from-coconut-oil-69d4233c (ID: 202) from ADM (Supplier ID: 1)
  3. RM-C6-soy-lecithin-5de90202 (ID: 215) from ADM (Supplier ID: 1)

### Code Quality

- ✓ Type hints throughout
- ✓ Comprehensive docstrings
- ✓ Robust error handling
- ✓ Detailed logging of schema detection
- ✓ No hardcoded schema assumptions
- ✓ All modules import successfully
- ✓ Production-ready Python code

### Testing Commands

```bash
# Inspect the database schema and source data
python main.py inspect-source

# Verify enrichment discovery works
python -c "from enrich_raw_materials import discover_raw_material_sources; mats = discover_raw_material_sources(); print(f'Discovered {len(mats)} raw materials')"

# Run enrichment pipeline (when Ollama is available)
python main.py enrich
```

### Files Modified

1. **db.py** - Added schema introspection methods
2. **enrich_raw_materials.py** - Refactored to use dynamic schema discovery
3. **main.py** - Added inspect-source command

### Backward Compatibility

All existing functionality is preserved:
- `compare_products()` - Unchanged
- `suggest_alternatives()` - Unchanged
- Database tables (raw_material_master, raw_material_embeddings, raw_material_comparisons) - Unchanged
- Ollama client integration - Unchanged
