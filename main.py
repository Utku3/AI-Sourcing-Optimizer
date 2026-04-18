#!/usr/bin/env python3
"""
Main entry point for the raw material substitution system.
"""

import argparse
import logging
import sys
from typing import Optional
from db import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize the database with schema."""
    logger.info("Setting up database schema")
    with open("schema.sql", "r") as f:
        schema_sql = f.read()

    with db.get_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Database schema initialized")

def run_enrichment():
    """Run the enrichment pipeline."""
    from enrich_raw_materials import enrich_raw_materials
    logger.info("Running enrichment pipeline")
    enrich_raw_materials()

def compare_command(product_id_a: int, supplier_id_a: int,
                   product_id_b: int, supplier_id_b: int):
    """Compare two products."""
    from comparison_engine import compare_products
    try:
        result = compare_products(product_id_a, supplier_id_a, product_id_b, supplier_id_b)
        print("Comparison Result:")
        print(f"Product A: {result['product_id_a']}")
        print(f"Product B: {result['product_id_b']}")
        print(f"General Score: {result['general_comparison_score']:.3f}")
        print(f"Label: {result['comparison_label']}")
        print(f"Reason: {result['comparison_reason']}")
        print("\nDetailed Scores:")
        print(f"Taste: {result['taste_score']:.3f}")
        print(f"Feasibility: {result['feasibility_score']:.3f}")
        print(f"Usage: {result['usage_score']:.3f}")
        print(f"Confidence: {result['confidence_score']:.3f}")
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        sys.exit(1)

def suggest_command(product_id: int, supplier_id: Optional[int] = None):
    """Suggest alternatives for a product."""
    from service import suggest_alternatives
    try:
        result = suggest_alternatives(product_id, supplier_id)
        print(f"Alternatives for {result['source_product']['product_name']} "
              f"(class: {result['source_product']['product_class']}):")
        print()

        if not result["alternatives"]:
            print("No suitable alternatives found.")
            return

        for i, alt in enumerate(result["alternatives"], 1):
            comp = alt["comparison"]
            print(f"{i}. {alt['product_name']}")
            print(f"   Score: {comp['general_comparison_score']:.3f} ({comp['comparison_label']})")
            print(f"   Reason: {comp['comparison_reason']}")
            print()

    except Exception as e:
        logger.error(f"Suggestion failed: {e}")
        sys.exit(1)

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Raw Material Substitution System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Initialize database schema")

    # Enrich command
    subparsers.add_parser("enrich", help="Run enrichment pipeline")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two products")
    compare_parser.add_argument("product_a", type=int, help="Product ID A")
    compare_parser.add_argument("supplier_a", type=int, help="Supplier ID A")
    compare_parser.add_argument("product_b", type=int, help="Product ID B")
    compare_parser.add_argument("supplier_b", type=int, help="Supplier ID B")

    # Suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest alternatives")
    suggest_parser.add_argument("product", type=int, help="Product ID")
    suggest_parser.add_argument("--supplier", type=int, help="Supplier ID (optional)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "setup":
            setup_database()
        elif args.command == "enrich":
            run_enrichment()
        elif args.command == "compare":
            compare_command(args.product_a, args.supplier_a, args.product_b, args.supplier_b)
        elif args.command == "suggest":
            suggest_command(args.product, args.supplier)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()