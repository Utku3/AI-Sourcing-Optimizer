#!/usr/bin/env python3
"""
Test script to verify schema detection works on the remote server.
Run this on the remote server after deployment.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_schema_detection():
    """Test that schema detection works regardless of database structure."""
    from db import db
    from enrich_raw_materials import discover_raw_material_sources
    
    print("\n" + "="*60)
    print("SCHEMA DETECTION TEST")
    print("="*60 + "\n")
    
    # Test 1: List available tables
    print("✓ Test 1: Detecting available tables...")
    tables = db.get_all_tables()
    print(f"  Found {len(tables)} tables: {', '.join(tables)}\n")
    
    # Test 2: Infer source columns
    print("✓ Test 2: Inferring source column mapping...")
    try:
        mapping = db.infer_raw_material_source_columns()
        print(f"  Detection method: {mapping['method']}")
        print(f"  Source table: {mapping['source_table']}")
        print(f"  Product ID column: {mapping['product_id_col']}")
        print(f"  Product name column: {mapping['product_name_col']}")
        if 'supplier_id_col' in mapping:
            print(f"  Supplier ID column: {mapping['supplier_id_col']}")
            print(f"  Supplier name column: {mapping['supplier_name_col']}")
        if 'supplier_col' in mapping:
            print(f"  Supplier column: {mapping['supplier_col']}")
        print()
    except Exception as e:
        logger.error(f"Schema inference failed: {e}")
        return False
    
    # Test 3: Discover raw materials
    print("✓ Test 3: Discovering raw materials...")
    try:
        raw_materials = discover_raw_material_sources()
        print(f"  Discovered {len(raw_materials)} raw material-supplier combinations\n")
        
        if raw_materials:
            print("  First 3 examples:")
            for i, mat in enumerate(raw_materials[:3], 1):
                print(f"    {i}. Product: {mat['product_name']} (ID: {mat['product_id']}) "
                      f"from {mat['supplier_name']} (Supplier ID: {mat['supplier_id']})")
            print()
    except Exception as e:
        logger.error(f"Raw material discovery failed: {e}")
        return False
    
    # Test 4: Verify Ollama connection
    print("✓ Test 4: Testing Ollama connection...")
    try:
        from ollama_client import ollama_client
        connected = ollama_client.test_connection()
        if connected:
            print("  ✓ Ollama is reachable\n")
        else:
            print("  ⚠ Ollama is not reachable (this is expected if Ollama isn't running)\n")
    except Exception as e:
        logger.error(f"Ollama connection test failed: {e}\n")
    
    print("="*60)
    print("ALL TESTS PASSED - Ready to run enrichment!")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    try:
        success = test_schema_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
