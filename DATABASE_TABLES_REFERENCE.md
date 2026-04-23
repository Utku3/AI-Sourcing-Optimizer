# Database Tables - Complete Reference After Enrichment

## Overview

After enrichment completes, your friend will have **9 tables** in the SQLite database:

### Source Data Tables (Pre-existing)
1. **Company** - 61 rows
2. **Product** - 1,025 rows  
3. **BOM** - 149 rows
4. **BOM_Component** - 1,528 rows
5. **Supplier** - 40 rows
6. **Supplier_Product** - 1,633 rows

### Enriched Data Tables (Created by enrichment)
7. **raw_material_master** - Will have 1,633 rows
8. **raw_material_embeddings** - Will have 1,633 rows
9. **raw_material_comparisons** - Grows as comparisons are made

---

## Source Data Tables (Already Exist)

### Table 1: Company
**Purpose:** Store company/organization information
**Rows:** 61

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| CompanyId | INTEGER | 1 | Primary key |
| CompanyName | TEXT | "Acme Corp" | Company name |
| Country | TEXT | "Turkey" | Location |
| ContactPerson | TEXT | "John Smith" | Contact name |
| Email | TEXT | "john@acme.com" | Contact email |
| Phone | TEXT | "+90-212-555-1234" | Contact phone |

**Sample Data:**
```
CompanyId | CompanyName        | Country
1         | Acme Corp          | Turkey
2         | Global Foods Inc   | USA
3         | Premium Ingredients| EU
...
```

---

### Table 2: Product  
**Purpose:** All products (finished goods and raw materials)
**Rows:** 1,025

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| Id | INTEGER | 1 | Primary key |
| SKU | TEXT | "RM-FLOUR-001" | Product code |
| Type | TEXT | "raw-material" | "raw-material" or "finished-good" |
| Name | TEXT | "All-Purpose Flour Premium" | Product name |
| ManufacturerId | INTEGER | 5 | Links to Company |
| Description | TEXT | "High quality wheat flour" | Product description |

**Sample Data:**
```
Id  | SKU              | Type           | Name                      | ManufacturerId
1   | RM-FLOUR-001     | raw-material   | All-Purpose Flour         | 1
2   | RM-SUGAR-001     | raw-material   | White Granulated Sugar    | 2
3   | FG-BREAD-001     | finished-good  | Artisan Bread             | 5
...
```

---

### Table 3: Supplier
**Purpose:** Supplier companies
**Rows:** 40

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| Id | INTEGER | 1 | Primary key |
| Name | TEXT | "Acme Foods Inc" | Supplier name |
| Country | TEXT | "Turkey" | Location |
| ContactEmail | TEXT | "sales@acme.com" | Contact |
| TaxNumber | TEXT | "12345678901" | Tax ID |
| Rating | REAL | 4.5 | Quality rating (0-5) |

**Sample Data:**
```
Id | Name                | Country | ContactEmail        | Rating
1  | Acme Foods Inc      | Turkey  | sales@acme.com      | 4.8
2  | Superior Ingred Ltd | EU      | contact@superior.eu | 4.2
3  | Quality Imports Co  | USA     | info@qualityimport..| 4.5
...
```

---

### Table 4: Supplier_Product
**Purpose:** Links which suppliers supply which products
**Rows:** 1,633 (this becomes raw_material_master after enrichment)

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| SupplierId | INTEGER | 1 | Links to Supplier |
| ProductId | INTEGER | 1 | Links to Product |
| SupplierSKU | TEXT | "FLOUR-ACM-001" | Supplier's product code |
| UnitPrice | REAL | 2.50 | Price per unit |
| Currency | TEXT | "USD" | Currency |
| MinOrderQty | INTEGER | 100 | Minimum order quantity |

**Sample Data:**
```
SupplierId | ProductId | SupplierSKU      | UnitPrice | Currency
1          | 1         | FLOUR-ACM-001    | 2.50      | USD
1          | 2         | SUGAR-ACM-001    | 1.80      | USD
2          | 1         | FLOUR-SUP-001    | 2.45      | USD
2          | 3         | BUTTER-SUP-001   | 5.00      | USD
...
```

---

### Table 5: BOM (Bill of Materials)
**Purpose:** Recipes - which raw materials go into finished goods
**Rows:** 149

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| BOMId | INTEGER | 1 | Primary key |
| FinishedGoodId | INTEGER | 10 | Links to Product (finished-good) |
| Version | INTEGER | 1 | Recipe version |
| CreatedDate | DATE | 2024-01-15 | When created |

**Sample Data:**
```
BOMId | FinishedGoodId | Version | CreatedDate
1     | 10             | 1       | 2024-01-15
2     | 11             | 1       | 2024-01-20
3     | 12             | 2       | 2024-02-01
...
```

---

### Table 6: BOM_Component
**Purpose:** Individual raw materials in each recipe
**Rows:** 1,528

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| BOMComponentId | INTEGER | 1 | Primary key |
| BOMId | INTEGER | 1 | Links to BOM |
| RawMaterialId | INTEGER | 1 | Links to Product (raw-material) |
| Quantity | REAL | 5.0 | Amount needed |
| Unit | TEXT | "kg" | Unit of measurement |
| Sequence | INTEGER | 1 | Order in recipe (1st, 2nd, etc) |

**Sample Data:**
```
BOMComponentId | BOMId | RawMaterialId | Quantity | Unit | Sequence
1              | 1     | 1            | 5.0      | kg   | 1
2              | 1     | 2            | 2.5      | kg   | 2
3              | 1     | 3            | 1.0      | kg   | 3
4              | 2     | 4            | 3.0      | L    | 1
...
```

---

## Enriched Data Tables (Created During Enrichment)

### Table 7: raw_material_master ⭐
**Purpose:** Enriched raw material data with AI-extracted information
**Rows:** Will have 1,633 rows (one per supplier-product combination)
**Created By:** Enrichment pipeline calling Ollama

| Column Name | Data Type | Size | Example | Notes |
|------------|-----------|------|---------|-------|
| product_id | INTEGER | - | 1 | From Product.Id |
| product_name | TEXT | - | "All-Purpose Flour" | Product name |
| product_json | TEXT | ~500 bytes | JSON string | Full enriched data from Ollama |
| product_class | TEXT | - | "flour" | Category extracted from product_json |
| supplier_id | INTEGER | - | 1 | From Supplier.Id |
| supplier_name | TEXT | - | "Acme Foods Inc" | Supplier name |
| supplier_json | TEXT | ~200 bytes | JSON string | Supplier summary |

**PRIMARY KEY:** (product_id, supplier_id)

**Sample Data:**

| product_id | product_name | product_class | supplier_id | supplier_name | product_json |
|----------|-------------|---------------|----------|--------------|-------------|
| 1 | All-Purpose Flour | flour | 1 | Acme Foods Inc | `{"cleaned_canonical_name": "All-Purpose Flour Premium Blend", "general_class": "flour", "ingredient_type": "grain", "functional_role": "base_ingredient", "physical_form": "powder", "application_domain": "baking", "synonyms": ["wheat flour", "all purpose flour"], "short_embedding_text": "Premium all-purpose wheat flour for baking", "confidence": 0.95, "taste": "neutral"}` |
| 1 | All-Purpose Flour | flour | 2 | Superior Ingred | `{"cleaned_canonical_name": "All-Purpose Flour", "general_class": "flour", "ingredient_type": "grain", "functional_role": "base_ingredient", "physical_form": "powder", "application_domain": "baking", "synonyms": ["flour", "wheat flour"], "short_embedding_text": "Quality all-purpose flour", "confidence": 0.93, "taste": "neutral"}` |
| 2 | White Sugar | sugar | 1 | Acme Foods Inc | `{"cleaned_canonical_name": "White Granulated Sugar", "general_class": "sweetener", "ingredient_type": "carbohydrate", "functional_role": "sweetener", "physical_form": "granulated", "application_domain": "baking", "synonyms": ["sugar", "white sugar", "granulated sugar"], "short_embedding_text": "Pure white granulated sugar for sweetening", "confidence": 0.98, "taste": "sweet"}` |
| 3 | Butter | butter | 2 | Superior Ingred | `{"cleaned_canonical_name": "Unsalted Butter", "general_class": "fat", "ingredient_type": "dairy", "functional_role": "shortening", "physical_form": "solid", "application_domain": "baking", "synonyms": ["butter", "unsalted butter"], "short_embedding_text": "Premium unsalted butter for baking", "confidence": 0.96, "taste": "creamy, buttery"}` |
| ... | ... | ... | ... | ... | ... |

**What's in product_json (extracted by Ollama):**
```json
{
  "cleaned_canonical_name": "All-Purpose Flour Premium Blend",
  "general_class": "flour",
  "ingredient_type": "grain",
  "functional_role": "base_ingredient",
  "physical_form": "powder",
  "application_domain": "baking",
  "synonyms": ["wheat flour", "all purpose flour", "bread flour"],
  "short_embedding_text": "Premium all-purpose wheat flour for baking with 11-12% protein",
  "confidence": 0.95,
  "taste": "neutral, clean"
}
```

**Rows per supplier:**
```
Supplier 1 (Acme): 350 products
Supplier 2 (Superior): 280 products
Supplier 3 (Quality): 220 products
... (40 suppliers total)
Total: 1,633 rows
```

**Data Size:**
- Each row: ~700 bytes (product_json + supplier_json)
- Total table: ~1.1 MB

---

### Table 8: raw_material_embeddings ⭐
**Purpose:** Vector embeddings for semantic similarity search
**Rows:** Will have 1,633 rows
**Created By:** Enrichment pipeline using sentence-transformers

| Column Name | Data Type | Size | Example |
|------------|-----------|------|---------|
| product_id | INTEGER | - | 1 |
| supplier_id | INTEGER | - | 1 |
| embedding_text | TEXT | ~200 bytes | "All-Purpose Flour Premium Blend - grain-based ingredient for baking" |
| embedding_model | TEXT | - | "all-MiniLM-L6-v2" |
| embedding_vector | BLOB | 1,536 bytes | Binary vector (384 dimensions × 4 bytes) |

**PRIMARY KEY:** (product_id, supplier_id)

**Sample Data:**

| product_id | supplier_id | embedding_model | embedding_vector (first 5 values shown) |
|----------|-----------|-----------------|-------------------------|
| 1 | 1 | all-MiniLM-L6-v2 | `[0.023, -0.156, 0.089, 0.042, -0.078, ...]` (384 total) |
| 1 | 2 | all-MiniLM-L6-v2 | `[0.025, -0.152, 0.091, 0.039, -0.081, ...]` (384 total) |
| 2 | 1 | all-MiniLM-L6-v2 | `[-0.041, 0.123, -0.067, 0.156, 0.012, ...]` (384 total) |
| 3 | 2 | all-MiniLM-L6-v2 | `[0.088, -0.045, 0.172, -0.033, 0.067, ...]` (384 total) |

**Why embeddings matter:**
- Same material from different suppliers → Similar vectors
- Different materials → Different vectors
- Used to find similar products quickly

**Data Size:**
- Each row: 1,536 bytes (for 384-dimensional float32 vector)
- Total table: ~2.5 MB

---

### Table 9: raw_material_comparisons ⭐
**Purpose:** Cache comparison results between products
**Rows:** Grows over time as comparisons are made
**Created By:** Comparison engine (when you run suggest/compare commands)

| Column Name | Data Type | Example | Notes |
|------------|-----------|---------|-------|
| product_id_a | INTEGER | 1 | First product |
| supplier_id_a | INTEGER | 1 | First supplier |
| product_id_b | INTEGER | 1 | Second product |
| supplier_id_b | INTEGER | 2 | Second supplier |
| taste_score | REAL | 0.82 | Taste compatibility (0-1) |
| feasibility_score | REAL | 0.91 | Process compatibility (0-1) |
| usage_score | REAL | 0.85 | Usage compatibility (0-1) |
| confidence_score | REAL | 0.88 | AI confidence (0-1) |
| general_comparison_score | REAL | 0.85 | Overall score (0-1) |
| comparison_label | TEXT | "Good Alternative" | Category label |
| comparison_reason | TEXT | "Both are premium flours..." | Explanation |

**PRIMARY KEY:** (product_id_a, supplier_id_a, product_id_b, supplier_id_b)

**Sample Data:**

| product_id_a | supplier_id_a | product_id_b | supplier_id_b | taste_score | feasibility_score | usage_score | confidence_score | general_score | comparison_label |
|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| 1 | 1 | 1 | 2 | 0.95 | 0.92 | 0.90 | 0.93 | 0.92 | Perfect Match |
| 1 | 1 | 2 | 1 | 0.15 | 0.10 | 0.08 | 0.95 | 0.11 | Incompatible |
| 2 | 1 | 2 | 2 | 0.98 | 0.95 | 0.93 | 0.96 | 0.95 | Perfect Match |
| 3 | 1 | 3 | 2 | 0.78 | 0.82 | 0.80 | 0.85 | 0.81 | Good Alternative |
| 1 | 2 | 1 | 3 | 0.88 | 0.85 | 0.87 | 0.89 | 0.87 | Good Alternative |

**Comparison Labels:**
- **Perfect Match:** Score >= 0.90
- **Good Alternative:** Score 0.75-0.89
- **Acceptable:** Score 0.60-0.74
- **Poor Match:** Score 0.40-0.59
- **Incompatible:** Score < 0.40

**Example Comparison Result:**
```
Comparing: Flour (Supplier 1) vs Flour (Supplier 2)
- Taste Score: 0.95 (flavors very similar)
- Feasibility Score: 0.92 (can use in same process)
- Usage Score: 0.90 (customers won't notice difference)
- Confidence Score: 0.93 (AI is 93% sure)
- GENERAL SCORE: 0.92 → "Perfect Match" ✓
- Reason: "Both are premium all-purpose flours with 11-12% protein content..."
```

**Growth Over Time:**
- After enrichment (no comparisons yet): 0 rows
- After 10 product comparisons: 10 rows
- After 100 product comparisons: 100 rows
- After 1000 product comparisons: 1,000 rows
- Examples: 1,633 products × 1,633 products = 2.67M possible comparisons (but only stores actual comparisons)

---

## Summary: Total Database Size

After enrichment completes:

| Table Name | Rows | Size | Purpose |
|-----------|------|------|---------|
| Company | 61 | ~15 KB | Company info |
| Product | 1,025 | ~100 KB | Products catalog |
| Supplier | 40 | ~10 KB | Supplier info |
| Supplier_Product | 1,633 | ~150 KB | Supplier-product links |
| BOM | 149 | ~20 KB | Recipes |
| BOM_Component | 1,528 | ~100 KB | Recipe items |
| **raw_material_master** | **1,633** | **~1.1 MB** | ⭐ **Enriched data** |
| **raw_material_embeddings** | **1,633** | **~2.5 MB** | ⭐ **Vector embeddings** |
| **raw_material_comparisons** | 0-1000s | ~100 KB-5 MB | ⭐ **Comparison cache** |

**Total Database Size:** ~4-5 MB (grows as comparisons are made)

---

## Viewing the Data After Enrichment

### Check what was created:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
tables = [row[0] for row in cur.fetchall()]
print('Tables:', tables)

# Show row counts
for table in tables:
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    count = cur.fetchone()[0]
    print(f'{table}: {count} rows')
"
```

### View sample enriched data:
```bash
python -c "
import sqlite3
import json
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute('SELECT product_id, product_name, product_class, supplier_name, product_json FROM raw_material_master LIMIT 3')
for row in cur.fetchall():
    product_id, product_name, product_class, supplier_name, product_json = row
    data = json.loads(product_json)
    print(f'Product: {product_name} (Class: {product_class})')
    print(f'Supplier: {supplier_name}')
    print(f'Details: {data}')
    print()
"
```

### View embeddings:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite')
cur = conn.cursor()
cur.execute('SELECT product_id, supplier_id, embedding_model, LENGTH(embedding_vector) FROM raw_material_embeddings LIMIT 3')
for row in cur.fetchall():
    product_id, supplier_id, model, vector_size = row
    print(f'Product {product_id} from Supplier {supplier_id}: {model} ({vector_size} bytes)')
"
```

---

## What Happens After Enrichment

### Step 1: raw_material_master is populated
1,633 rows with AI-extracted data from Ollama

### Step 2: raw_material_embeddings is populated
1,633 rows with vector embeddings from sentence-transformers

### Step 3: System is ready for queries
When you run:
```bash
python main.py suggest 1
python main.py compare 1 1 2 1
```

The system queries these 3 tables to provide results.

### Step 4: raw_material_comparisons grows
Each time you compare products, results are cached in this table (for fast repeated queries)

---

## Expected Final Statistics

After enrichment on friend's server:

```
✓ raw_material_master: 1,633 rows (enriched materials)
✓ raw_material_embeddings: 1,633 rows (vector data)
✓ raw_material_comparisons: 0 rows initially (grows with usage)

✓ Database ready for:
  - Suggestions
  - Comparisons
  - Similarity searches
  - Supplier evaluation
```

**All data is stored locally in SQLite - no external service needed** ✅
