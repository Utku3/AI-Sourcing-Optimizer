import sqlite3
import os
from typing import List, Tuple, Dict, Any, Optional
import json
import pickle

class Database:
    """Database connection and utility class for the raw material substitution system."""

    def __init__(self, db_path: str = "db.sqlite"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def get_raw_materials_with_suppliers(self) -> List[Dict[str, Any]]:
        """Get raw materials with their suppliers from existing tables."""
        query = """
        SELECT
            p.Id as product_id,
            p.SKU as product_name,
            s.Id as supplier_id,
            s.Name as supplier_name
        FROM Product p
        JOIN Supplier_Product sp ON p.Id = sp.ProductId
        JOIN Supplier s ON sp.SupplierId = s.Id
        WHERE p.Type = 'raw-material'
        """
        rows = self.execute_query(query)
        return [
            {
                "product_id": row[0],
                "product_name": row[1],
                "supplier_id": row[2],
                "supplier_name": row[3]
            }
            for row in rows
        ]

    def insert_raw_material_master(self, data: Dict[str, Any]) -> None:
        """Insert or update raw material master data."""
        query = """
        INSERT OR REPLACE INTO raw_material_master
        (product_id, product_name, product_json, product_class, supplier_id, supplier_name, supplier_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["product_id"],
            data["product_name"],
            json.dumps(data.get("product_json", {})),
            data.get("product_class", ""),
            data["supplier_id"],
            data["supplier_name"],
            json.dumps(data.get("supplier_json", {}))
        )
        self.execute_update(query, params)

    def get_raw_material_master(self, product_id: int, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Get raw material master data by product and supplier ID."""
        query = """
        SELECT product_id, product_name, product_json, product_class, supplier_id, supplier_name, supplier_json
        FROM raw_material_master
        WHERE product_id = ? AND supplier_id = ?
        """
        rows = self.execute_query(query, (product_id, supplier_id))
        if rows:
            row = rows[0]
            return {
                "product_id": row[0],
                "product_name": row[1],
                "product_json": json.loads(row[2]) if row[2] else {},
                "product_class": row[3],
                "supplier_id": row[4],
                "supplier_name": row[5],
                "supplier_json": json.loads(row[6]) if row[6] else {}
            }
        return None

    def insert_embedding(self, product_id: int, supplier_id: int, embedding_text: str,
                        embedding_model: str, embedding_vector: bytes) -> None:
        """Insert or update embedding data."""
        query = """
        INSERT OR REPLACE INTO raw_material_embeddings
        (product_id, supplier_id, embedding_text, embedding_model, embedding_vector)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_update(query, (product_id, supplier_id, embedding_text, embedding_model, embedding_vector))

    def get_embedding(self, product_id: int, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Get embedding data by product and supplier ID."""
        query = """
        SELECT product_id, supplier_id, embedding_text, embedding_model, embedding_vector
        FROM raw_material_embeddings
        WHERE product_id = ? AND supplier_id = ?
        """
        rows = self.execute_query(query, (product_id, supplier_id))
        if rows:
            row = rows[0]
            return {
                "product_id": row[0],
                "supplier_id": row[1],
                "embedding_text": row[2],
                "embedding_model": row[3],
                "embedding_vector": pickle.loads(row[4]) if row[4] else []
            }
        return None

    def insert_comparison(self, comparison_data: Dict[str, Any]) -> None:
        """Insert comparison result."""
        query = """
        INSERT OR REPLACE INTO raw_material_comparisons
        (product_id_a, supplier_id_a, product_id_b, supplier_id_b,
         taste_score, feasibility_score, usage_score, confidence_score,
         general_comparison_score, comparison_label, comparison_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            comparison_data["product_id_a"],
            comparison_data["supplier_id_a"],
            comparison_data["product_id_b"],
            comparison_data["supplier_id_b"],
            comparison_data["taste_score"],
            comparison_data["feasibility_score"],
            comparison_data["usage_score"],
            comparison_data["confidence_score"],
            comparison_data["general_comparison_score"],
            comparison_data["comparison_label"],
            comparison_data["comparison_reason"]
        )
        self.execute_update(query, params)

    def get_comparison(self, product_id_a: int, supplier_id_a: int,
                      product_id_b: int, supplier_id_b: int) -> Optional[Dict[str, Any]]:
        """Get comparison result between two products."""
        query = """
        SELECT product_id_a, supplier_id_a, product_id_b, supplier_id_b,
               taste_score, feasibility_score, usage_score, confidence_score,
               general_comparison_score, comparison_label, comparison_reason
        FROM raw_material_comparisons
        WHERE product_id_a = ? AND supplier_id_a = ? AND product_id_b = ? AND supplier_id_b = ?
        """
        rows = self.execute_query(query, (product_id_a, supplier_id_a, product_id_b, supplier_id_b))
        if rows:
            row = rows[0]
            return {
                "product_id_a": row[0],
                "supplier_id_a": row[1],
                "product_id_b": row[2],
                "supplier_id_b": row[3],
                "taste_score": row[4],
                "feasibility_score": row[5],
                "usage_score": row[6],
                "confidence_score": row[7],
                "general_comparison_score": row[8],
                "comparison_label": row[9],
                "comparison_reason": row[10]
            }
        return None

    def get_products_by_class(self, product_class: str) -> List[Dict[str, Any]]:
        """Get all products in a specific class."""
        query = """
        SELECT product_id, supplier_id, product_name, product_json
        FROM raw_material_master
        WHERE product_class = ?
        """
        rows = self.execute_query(query, (product_class,))
        return [
            {
                "product_id": row[0],
                "supplier_id": row[1],
                "product_name": row[2],
                "product_json": json.loads(row[3]) if row[3] else {}
            }
            for row in rows
        ]

# Global database instance
db = Database()