#!/usr/bin/env python3
"""
Script to enrich raw materials with structured data from Qwen API.
"""

import logging
import sys
from typing import Dict, Any
import pickle
from db import db
from config import config
from name_cleaning import clean_product_name
from qwen_client import qwen_client
from embedding_text_builder import build_embedding_text
from embeddings import embedding_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def enrich_raw_materials():
    """Enrich all raw materials with Qwen API data."""
    logger.info("Starting raw material enrichment process")

    # Get all raw materials with suppliers
    raw_materials = db.get_raw_materials_with_suppliers()
    logger.info(f"Found {len(raw_materials)} raw material-supplier combinations")

    enriched_count = 0
    error_count = 0

    for material in raw_materials:
        try:
            logger.info(f"Processing: {material['product_name']} from {material['supplier_name']}")

            # Clean product name
            cleaned_name = clean_product_name(material['product_name'])

            # Prepare supplier data (could be expanded)
            supplier_data_text = f"Supplier: {material['supplier_name']}"

            # Call Qwen API
            structured_data = qwen_client.get_product_structured_data(
                original_product_name=material['product_name'],
                cleaned_product_name=cleaned_name,
                supplier_name=material['supplier_name'],
                supplier_data_text=supplier_data_text,
                allowed_classes=config.ALLOWED_CLASSES
            )

            # Prepare data for storage
            supplier_summary = qwen_client.get_supplier_summary_json(
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