#!/usr/bin/env python3
"""
Script to enrich raw materials with structured data from Ollama API.
"""

import logging
import sys
from typing import Dict, Any, List
import pickle
from db import db
from config import config
from name_cleaning import clean_product_name
from ollama_client import ollama_client
from embedding_text_builder import build_embedding_text
from embeddings import embedding_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def discover_raw_material_sources() -> List[Dict[str, Any]]:
    """Discover and fetch raw materials from the database using schema introspection."""
    logger.info("Discovering raw material sources...")
    
    # Get the inferred column mapping
    mapping = db.infer_raw_material_source_columns()
    logger.info(f"Using mapping: {mapping}")
    
    # Build dynamic query based on discovered schema
    if mapping["method"] == "standard_join":
        query = f"""
        SELECT
            p.{mapping['product_id_col']} as product_id,
            p.{mapping['product_name_col']} as product_name,
            s.{mapping['supplier_id_col']} as supplier_id,
            s.{mapping['supplier_name_col']} as supplier_name
        FROM {mapping['source_table']} p
        JOIN {mapping['join_table']} sp ON p.{mapping['product_id_col']} = sp.ProductId
        JOIN {mapping['supplier_table']} s ON sp.SupplierId = s.{mapping['supplier_id_col']}
        WHERE p.{mapping['product_type_col']} = ?
        """
        rows = db.execute_query(query, (mapping['product_type_filter'],))
        logger.info(f"Query used: {query}")
    else:
        raise ValueError(f"Unsupported method: {mapping['method']}")
    
    raw_materials = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "supplier_id": row[2],
            "supplier_name": row[3]
        }
        for row in rows
    ]
    
    logger.info(f"Discovered {len(raw_materials)} raw material-supplier combinations")
    logger.info(f"Source columns used: product_id={mapping['product_id_col']}, "
                f"product_name={mapping['product_name_col']}, "
                f"supplier_id={mapping['supplier_id_col']}, "
                f"supplier_name={mapping['supplier_name_col']}")
    
    return raw_materials

def enrich_raw_materials():
    """Enrich all raw materials with Ollama API data."""
    logger.info("Starting raw material enrichment process")

    try:
        # Discover raw materials using schema introspection
        raw_materials = discover_raw_material_sources()
    except Exception as e:
        logger.error(f"Failed to discover raw material sources: {e}")
        raise

    enriched_count = 0
    error_count = 0

    for material in raw_materials:
        try:
            logger.info(f"Processing: {material['product_name']} from {material['supplier_name']}")

            # Clean product name
            cleaned_name = clean_product_name(material['product_name'])

            # Prepare supplier data
            supplier_data_text = f"Supplier: {material['supplier_name']}"

            # Call Ollama API
            structured_data = ollama_client.get_product_structured_data(
                original_product_name=material['product_name'],
                cleaned_product_name=cleaned_name,
                supplier_name=material['supplier_name'],
                supplier_data_text=supplier_data_text,
                allowed_classes=config.ALLOWED_CLASSES
            )

            # Prepare data for storage
            supplier_summary = ollama_client.get_supplier_summary_json(
                supplier_name=material["supplier_name"],
                supplier_data_text=supplier_data_text
            )

            master_data = {
                "product_id": material["product_id"],
                "product_name": material["product_name"],
                "product_json": structured_data,
                "product_class": structured_data["general_class"],
                "supplier_id": material["supplier_id"],
                "supplier_name": material["supplier_name"],
                "supplier_json": supplier_summary
            }

            # Store in database
            db.insert_raw_material_master(master_data)

            # Generate and store embedding
            embedding_text = build_embedding_text(structured_data)
            embedding_vector = embedding_service.generate_embedding(embedding_text)
            embedding_vector_blob = pickle.dumps(embedding_vector)

            db.insert_embedding(
                material["product_id"],
                material["supplier_id"],
                embedding_text,
                embedding_service.get_model_name(),
                embedding_vector_blob
            )

            enriched_count += 1
            logger.info(f"Successfully enriched: {material['product_name']}")

        except Exception as e:
            logger.error(f"Failed to enrich {material['product_name']}: {e}")
            error_count += 1

    logger.info(f"Enrichment complete. Enriched: {enriched_count}, Errors: {error_count}")

def main():
    """Main entry point."""
    try:
        enrich_raw_materials()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()