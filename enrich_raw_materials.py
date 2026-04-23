#!/usr/bin/env python3
"""
Script to enrich raw materials with structured data from Ollama API.
"""

import logging
import sys
import time
import threading
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


def find_unenriched_materials() -> List[Dict[str, Any]]:
    """Return only source materials that have no entry in raw_material_master yet."""
    mapping = db.infer_raw_material_source_columns()

    if mapping["method"] == "standard_join":
        query = f"""
        SELECT
            p.{mapping['product_id_col']},
            p.{mapping['product_name_col']},
            s.{mapping['supplier_id_col']},
            s.{mapping['supplier_name_col']}
        FROM {mapping['source_table']} p
        JOIN {mapping['join_table']} sp ON p.{mapping['product_id_col']} = sp.ProductId
        JOIN {mapping['supplier_table']} s ON sp.SupplierId = s.{mapping['supplier_id_col']}
        LEFT JOIN raw_material_master rmm
            ON p.{mapping['product_id_col']} = rmm.product_id
            AND s.{mapping['supplier_id_col']} = rmm.supplier_id
        WHERE p.{mapping['product_type_col']} = ?
          AND rmm.product_id IS NULL
        """
        rows = db.execute_query(query, (mapping['product_type_filter'],))
        return [
            {"product_id": r[0], "product_name": r[1], "supplier_id": r[2], "supplier_name": r[3]}
            for r in rows
        ]

    elif mapping["method"] == "product_finished_good":
        query = f"""
        SELECT
            pfg.{mapping['product_id_col']},
            pfg.{mapping['product_name_col']},
            pfg.{mapping['supplier_col']}
        FROM {mapping['source_table']} pfg
        LEFT JOIN raw_material_master rmm ON pfg.{mapping['product_id_col']} = rmm.product_id
        WHERE rmm.product_id IS NULL
        """
        rows = db.execute_query(query)
        result = []
        for r in rows:
            supplier_name = r[2] if r[2] else "unknown"
            result.append({
                "product_id": r[0],
                "product_name": r[1],
                "supplier_id": abs(hash(supplier_name)) % (10 ** 8),
                "supplier_name": supplier_name,
            })
        return result

    raise ValueError(f"Unsupported method: {mapping['method']}")


def enrich_single_material(material: Dict[str, Any]) -> bool:
    """Enrich one material. Returns True on success, False on failure."""
    try:
        cleaned_name = clean_product_name(material['product_name'])
        supplier_data_text = f"Supplier: {material['supplier_name']}"

        structured_data = ollama_client.get_product_structured_data(
            original_product_name=material['product_name'],
            cleaned_product_name=cleaned_name,
            supplier_name=material['supplier_name'],
            supplier_data_text=supplier_data_text,
            allowed_classes=config.ALLOWED_CLASSES
        )

        supplier_summary = ollama_client.get_supplier_summary_json(
            supplier_name=material["supplier_name"],
            supplier_data_text=supplier_data_text
        )

        db.insert_raw_material_master({
            "product_id": material["product_id"],
            "product_name": material["product_name"],
            "product_json": structured_data,
            "product_class": structured_data["general_class"],
            "supplier_id": material["supplier_id"],
            "supplier_name": material["supplier_name"],
            "supplier_json": supplier_summary
        })

        embedding_text = build_embedding_text(structured_data)
        embedding_vector = embedding_service.generate_embedding(embedding_text)
        db.insert_embedding(
            material["product_id"],
            material["supplier_id"],
            embedding_text,
            embedding_service.get_model_name(),
            pickle.dumps(embedding_vector)
        )

        logger.info(f"Enriched: {material['product_name']}")
        return True

    except Exception as e:
        logger.error(f"Failed to enrich {material['product_name']}: {e}")
        return False


def enrich_raw_materials():
    """Enrich all unenriched raw materials."""
    logger.info("Starting raw material enrichment process")
    materials = find_unenriched_materials()
    logger.info(f"Found {len(materials)} unenriched materials")

    enriched, errors = 0, 0
    for material in materials:
        if enrich_single_material(material):
            enriched += 1
        else:
            errors += 1

    logger.info(f"Enrichment complete. Enriched: {enriched}, Errors: {errors}")


def watch_for_new_products(interval_seconds: int = 60):
    """Background loop: enrich any new products added to the source database."""
    logger.info(f"Product watcher started (checking every {interval_seconds}s)")
    while True:
        try:
            if not ollama_client.test_connection():
                logger.debug("Watcher: Ollama unreachable, skipping")
            else:
                new_materials = find_unenriched_materials()
                if new_materials:
                    logger.info(f"Watcher found {len(new_materials)} new product(s) — enriching")
                    for material in new_materials:
                        enrich_single_material(material)
                else:
                    logger.debug("Watcher: no new products found")
        except Exception as e:
            logger.error(f"Watcher error: {e}")
        time.sleep(interval_seconds)


def start_watcher(interval_seconds: int = 60) -> threading.Thread:
    """Start the product watcher as a daemon thread. Call this from app.py."""
    thread = threading.Thread(
        target=watch_for_new_products,
        args=(interval_seconds,),
        daemon=True,
        name="product-watcher"
    )
    thread.start()
    return thread


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
