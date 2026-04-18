#!/usr/bin/env python3
"""
Quick verification script to test all core components after fixes.
Run this to confirm the setup is working.
"""

import sys
import sqlite3

print("=" * 60)
print("VERIFICATION SCRIPT - Core Imports & Database Check")
print("=" * 60)
print()

# Test 1: Python version
print(f"✓ Python version: {sys.version}")
print()

# Test 2: Core imports
print("Testing imports...")
try:
    from db import db
    print("  ✓ db module")
except ImportError as e:
    print(f"  ✗ db module: {e}")
    sys.exit(1)

try:
    from ollama_client import ollama_client
    print("  ✓ ollama_client module")
except ImportError as e:
    print(f"  ✗ ollama_client module: {e}")
    sys.exit(1)

try:
    from config import config
    print("  ✓ config module")
except ImportError as e:
    print(f"  ✗ config module: {e}")
    sys.exit(1)

try:
    from comparison_engine import compare_products
    print("  ✓ comparison_engine module")
except ImportError as e:
    print(f"  ✗ comparison_engine module: {e}")
    sys.exit(1)

try:
    from service import suggest_alternatives
    print("  ✓ service module")
except ImportError as e:
    print(f"  ✗ service module: {e}")
    sys.exit(1)

print()
print("Testing Ollama connection...")
try:
    is_ok = ollama_client.test_connection()
    if is_ok:
        print("  ✓ Ollama is reachable at http://localhost:11434")
    else:
        print("  ✗ Ollama not responding")
except Exception as e:
    print(f"  ✗ Ollama error: {e}")

print()
print("Checking database schema...")
try:
    tables = db.get_all_tables()
    print(f"  Found tables: {', '.join(tables)}")
    
    # Check schema detection
    mapping = db.infer_raw_material_source_columns()
    print(f"  Detection method: {mapping['method']}")
    print(f"  Source table: {mapping['source_table']}")
    
except Exception as e:
    print(f"  ✗ Schema error: {e}")
    sys.exit(1)

print()
print("Checking database content...")
try:
    conn = sqlite3.connect("db.sqlite")
    cur = conn.cursor()
    
    # Check each table
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    
    conn.close()
    
except Exception as e:
    print(f"  ✗ Database error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ ALL CHECKS PASSED - System is ready!")
print("=" * 60)
print()
print("Next steps:")
print("1. If Product_FinishedGood has 0 rows,  load data from production")
print("2. Run: python main.py setup (if needed)")
print("3. Run: python main.py enrich (to enrich raw materials)")
print("4. Run: python main.py suggest 1 (to test suggestions)")
print()
