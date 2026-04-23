# Testing Guide for Your Friend (Without Production Database)

## Problem
Your friend doesn't have access to the production database, so they can't test if the code works.

## Solution
Use the test database setup script to test locally with sample data.

## Quick Start

### Option 1: Test with Standard Schema (Local Style)

```bash
# Create test database with standard schema
python setup_test_database.py

# Verify schema was detected
python main.py inspect-source

# Run enrichment (will use Ollama if available)
python main.py enrich

# Test comparison
python main.py compare 1 1 2 1

# Test suggestions
python main.py suggest 1
```

**What it creates:**
- 10 test products (flour, sugar, butter, milk, eggs, etc.)
- 5 test suppliers (Acme Foods, Superior Ingredients, etc.)
- 12 supplier-product relationships

### Option 2: Test with Remote Schema (Product_FinishedGood Style)

```bash
# Create test database with remote schema
python setup_test_database.py remote

# Verify remote schema was detected
python main.py inspect-source

# Run enrichment
python main.py enrich

# Test suggestions
python main.py suggest 1
```

**What it creates:**
- 10 test products with "Market" field as supplier identifier
- No separate supplier table (replicates remote structure)

## Why This Works

1. **Test data is realistic**: Contains baking ingredients with multiple suppliers
2. **Two schema options**: Test both local (standard) and remote (Product_FinishedGood) schemas
3. **Automatic backups**: Old database is backed up before creating test data
4. **No production data needed**: Uses only sample data
5. **Full pipeline testing**: Can test schema detection, enrichment, comparison, and suggestions

## Testing Checklist

After creating test database, verify:

- [ ] `python main.py inspect-source` shows correct schema detection
- [ ] `python test_schema.py` runs without errors
- [ ] Database has expected tables and row counts
- [ ] Enrichment pipeline starts (even if Ollama not available)
- [ ] Comparison works: `python main.py compare 1 1 2 1`
- [ ] Suggestions work: `python main.py suggest 1`

## What Each Test Verifies

| Test | What It Checks |
|------|---|
| `inspect-source` | Schema detection working |
| `test_schema.py` | Table introspection, raw material discovery |
| `enrich` | Enrichment pipeline, Ollama connectivity |
| `compare` | Comparison scoring engine |
| `suggest` | Similarity calculations, ranking logic |

## Expected Output

### For standard schema:
```
Detection Method: standard_join
Source Table: Product
Total raw materials to enrich: 12
```

### For Product_FinishedGood schema:
```
Detection Method: product_finished_good
Source Table: Product_FinishedGood
Total raw materials to enrich: 10
```

## Restoring Original Database

If your friend had a production database, they can restore it:

```bash
# List backups
ls -la db.sqlite.backup.* 

# Restore specific backup
mv db.sqlite.backup.YYYYMMDD_HHMMSS db.sqlite
```

## If Tests Fail

### Ollama not available
- The enrichment step will fail if Ollama isn't running
- But schema detection, comparison, and suggestion functions will still work
- This is fine for testing the logic without the LLM

### Import errors
- Verify dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

### Database locked
- Close any other applications using the database
- Delete `db.sqlite-wal` files if they exist

## What Your Friend Should Report Back

After testing, they should tell you:

1. **Which schema was detected** (standard_join or product_finished_good?)
2. **How many raw materials** were discovered?
3. **Did enrichment start?** (Even if Ollama failed, was the pipeline called?)
4. **Did comparison work?** (Can it score two products?)
5. **Did suggestions work?** (Can it find alternatives?)

This will tell you if the core logic works independently of the production database.
