#!/usr/bin/env python3
"""
Create a test database with sample data for local testing.
This allows testing the enrichment pipeline without access to production databases.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def create_test_database_standard_schema():
    """Create test database with standard schema (local development style)."""
    # Backup existing database if it exists
    if os.path.exists("db.sqlite"):
        backup_name = f"db.sqlite.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy("db.sqlite", backup_name)
        print(f"✓ Backed up existing database to {backup_name}")
    
    # Create fresh database
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    
    # Create schema
    print("Creating standard schema tables...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Product (
            Id INTEGER PRIMARY KEY,
            SKU TEXT NOT NULL UNIQUE,
            Type TEXT NOT NULL,
            Name TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Supplier (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Supplier_Product (
            SupplierId INTEGER NOT NULL,
            ProductId INTEGER NOT NULL,
            SupplierSKU TEXT,
            FOREIGN KEY (SupplierId) REFERENCES Supplier(Id),
            FOREIGN KEY (ProductId) REFERENCES Product(Id),
            PRIMARY KEY (SupplierId, ProductId)
        )
    """)
    
    # Insert test data
    print("Inserting test data...")
    
    # Products
    test_products = [
        (1, "FLOUR-001", "Flour", "All-Purpose Flour"),
        (2, "SUGAR-001", "Sugar", "White Granulated Sugar"),
        (3, "BUTTER-001", "Butter", "Unsalted Butter"),
        (4, "MILK-001", "Dairy", "Whole Milk"),
        (5, "EGGS-001", "Eggs", "Large Brown Eggs"),
        (6, "VANILLA-001", "Extract", "Pure Vanilla Extract"),
        (7, "CHOCOLATE-001", "Cocoa", "Cocoa Powder"),
        (8, "YEAST-001", "Yeast", "Active Dry Yeast"),
        (9, "SALT-001", "Salt", "Sea Salt"),
        (10, "OIL-001", "Oil", "Olive Oil"),
    ]
    
    cursor.executemany(
        "INSERT INTO Product (Id, SKU, Type, Name) VALUES (?, ?, ?, ?)",
        test_products
    )
    
    # Suppliers
    test_suppliers = [
        (1, "Acme Foods Inc"),
        (2, "Superior Ingredients Ltd"),
        (3, "Quality Imports Co"),
        (4, "Global Suppliers"),
        (5, "Local Farms Cooperative"),
    ]
    
    cursor.executemany(
        "INSERT INTO Supplier (Id, Name) VALUES (?, ?)",
        test_suppliers
    )
    
    # Supplier-Product relationships
    test_supplier_products = [
        (1, 1, "FLOUR-ACM-001"),
        (1, 2, "SUGAR-ACM-001"),
        (2, 3, "BUTTER-SUP-001"),
        (2, 4, "MILK-SUP-001"),
        (3, 1, "FLOUR-QI-001"),
        (3, 5, "EGGS-QI-001"),
        (4, 6, "VANILLA-GS-001"),
        (4, 7, "COCOA-GS-001"),
        (5, 8, "YEAST-LF-001"),
        (5, 9, "SALT-LF-001"),
        (1, 10, "OIL-ACM-001"),
        (2, 6, "VANILLA-SUP-001"),
    ]
    
    cursor.executemany(
        "INSERT INTO Supplier_Product (SupplierId, ProductId, SupplierSKU) VALUES (?, ?, ?)",
        test_supplier_products
    )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created test database with standard schema")
    print(f"  - 10 products")
    print(f"  - 5 suppliers")
    print(f"  - 12 supplier-product relationships")


def create_test_database_product_finished_good_schema():
    """Create test database with Product_FinishedGood schema (remote server style)."""
    # Backup existing database if it exists
    if os.path.exists("db.sqlite"):
        backup_name = f"db.sqlite.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy("db.sqlite", backup_name)
        print(f"✓ Backed up existing database to {backup_name}")
    
    # Create fresh database
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    
    # Create schema
    print("Creating Product_FinishedGood schema tables...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Product_FinishedGood (
            ProductId INTEGER PRIMARY KEY,
            Market TEXT NOT NULL,
            MarketSearch TEXT NOT NULL,
            MarketAdditional TEXT
        )
    """)
    
    # Insert test data
    print("Inserting test data...")
    
    test_products = [
        (1, "Acme Foods Inc", "All-Purpose Flour Premium Blend", "Unbleached"),
        (2, "Acme Foods Inc", "White Granulated Sugar Refined", "Premium Grade"),
        (3, "Superior Ingredients Ltd", "Unsalted Butter European Style", "Cultured"),
        (4, "Superior Ingredients Ltd", "Whole Milk Organic", "Grass-Fed"),
        (5, "Quality Imports Co", "Large Brown Eggs Free Range", "Pasture Raised"),
        (6, "Quality Imports Co", "Pure Vanilla Extract Premium", "Madagascar"),
        (7, "Global Suppliers", "Cocoa Powder Dutch Processed", "Fair Trade"),
        (8, "Global Suppliers", "Active Dry Yeast Instant", "SAF-Instant"),
        (9, "Local Farms Cooperative", "Sea Salt Mediterranean", "Fine Grain"),
        (10, "Local Farms Cooperative", "Olive Oil Extra Virgin", "Cold Pressed"),
    ]
    
    cursor.executemany(
        "INSERT INTO Product_FinishedGood (ProductId, Market, MarketSearch, MarketAdditional) VALUES (?, ?, ?, ?)",
        test_products
    )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created test database with Product_FinishedGood schema")
    print(f"  - 10 products")
    print(f"  - Suppliers identified via 'Market' field")


def verify_database():
    """Verify database was created successfully."""
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n✓ Database verification:")
    print(f"  Tables: {', '.join([t[0] for t in tables])}")
    
    # Count rows in each table
    for table in [t[0] for t in tables]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    
    conn.close()


def main():
    """Main setup function."""
    import sys
    
    print("=" * 60)
    print("Test Database Setup")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "remote":
        print("Setting up test database with REMOTE schema (Product_FinishedGood)...")
        print()
        create_test_database_product_finished_good_schema()
    else:
        print("Setting up test database with LOCAL schema (Product + Supplier)...")
        print()
        create_test_database_standard_schema()
    
    print()
    verify_database()
    
    print()
    print("=" * 60)
    print("Next steps:")
    print("=" * 60)
    print()
    print("1. Verify schema detection:")
    print("   python main.py inspect-source")
    print()
    print("2. Run enrichment pipeline:")
    print("   python main.py enrich")
    print()
    print("3. Compare two products:")
    print("   python main.py compare 1 1 2 1")
    print()
    print("4. Suggest alternatives:")
    print("   python main.py suggest 1")
    print()
    print("To test with remote schema instead:")
    print("   python setup_test_database.py remote")
    print()


if __name__ == "__main__":
    main()
