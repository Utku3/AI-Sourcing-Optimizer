# Database Documentation

**File:** `db.sqlite`

## Overview

AI Sourcing Optimizer veri tabanı. Şirketlerin ürettiği ürünler (finished good & raw material), bill of materials (BOM) bağlantıları ve tedarikçi ilişkilerini tutar.

| Table | Rows | Açıklama |
|---|---|---|
| `Company` | 61 | Müşteri şirketler |
| `Product` | 1025 | Tüm ürünler (FG + RM) |
| `Product_FinishedGood` | 149 | FG detayları (market bilgisi) |
| `Product_RawMaterial` | 876 | RM detayları (malzeme adı) |
| `BOM` | 149 | Her FG için bir BOM kaydı |
| `BOM_Component` | 1528 | BOM → RM bağlantıları |
| `Supplier` | 40 | Tedarikçiler |
| `Supplier_Product` | 1633 | Tedarikçi → RM bağlantıları |

---

## Tables

### Company
Müşteri şirketleri tutar.

```sql
CREATE TABLE Company (
    Id   INTEGER PRIMARY KEY,
    Name TEXT NOT NULL
);
```

---

### Product
Sistemdeki tüm ürünlerin base tablosu. `Type` alanı ile FG ve RM ayrılır.

```sql
CREATE TABLE Product (
    Id        INTEGER PRIMARY KEY,
    SKU       TEXT NOT NULL,
    CompanyId INTEGER NOT NULL,
    Type      TEXT NOT NULL CHECK (Type IN ('finished-good', 'raw-material')),
    FOREIGN KEY (CompanyId) REFERENCES Company(Id)
);
```

**SKU formatları:**
- Finished Good: `FG-{market}-{market_search}` veya `FG-{market}-cen-{market_search}`
- Raw Material: `RM-C{company_id}-{material-name}-{unique_id}`

---

### Product_FinishedGood
`Product` tablosunu extend eder. Sadece `Type = 'finished-good'` olan ürünler için vardır.

```sql
CREATE TABLE Product_FinishedGood (
    ProductId        INTEGER PRIMARY KEY,
    Market           TEXT NOT NULL,
    MarketSearch     TEXT NOT NULL,
    MarketAdditional TEXT,
    FOREIGN KEY (ProductId) REFERENCES Product(Id)
);
```

| Kolon | Açıklama |
|---|---|
| `Market` | Ürünün satıldığı platform |
| `MarketSearch` | Platformda arama/ürün ID'si |
| `MarketAdditional` | Ek arama niteleyici (örn: `cen`) |

**Desteklenen marketler:** `amazon`, `costco`, `cvs`, `gnc`, `iherb`, `sams-club`, `target`, `the-vitamin-shoppe`, `thrive-market`, `vitacost`, `walgreens`, `walmart`

---

### Product_RawMaterial
`Product` tablosunu extend eder. Sadece `Type = 'raw-material'` olan ürünler için vardır.

```sql
CREATE TABLE Product_RawMaterial (
    ProductId    INTEGER PRIMARY KEY,
    CompanyId    INTEGER NOT NULL,
    MaterialName TEXT NOT NULL,
    UniqueId     TEXT NOT NULL,
    FOREIGN KEY (ProductId) REFERENCES Product(Id),
    FOREIGN KEY (CompanyId) REFERENCES Company(Id)
);
```

| Kolon | Açıklama |
|---|---|
| `CompanyId` | Bu RM'nin ait olduğu şirket (SKU'daki `C{id}` kısmı) |
| `MaterialName` | İnsan okunabilir malzeme adı (örn: `calcium citrate`) |
| `UniqueId` | SKU'nun son kısmındaki hash (örn: `05c28cc3`) |

---

### BOM
Her finished good için tek bir BOM (Bill of Materials) kaydı.

```sql
CREATE TABLE BOM (
    Id                INTEGER PRIMARY KEY,
    ProducedProductId INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (ProducedProductId) REFERENCES Product(Id)
);
```

---

### BOM_Component
Bir BOM'un içerdiği raw material'ları tutar. Bir BOM'un birden fazla bileşeni olabilir.

```sql
CREATE TABLE BOM_Component (
    BOMId             INTEGER NOT NULL,
    ConsumedProductId INTEGER NOT NULL,
    PRIMARY KEY (BOMId, ConsumedProductId),
    FOREIGN KEY (BOMId) REFERENCES BOM(Id),
    FOREIGN KEY (ConsumedProductId) REFERENCES Product(Id)
);
```

---

### Supplier
Tedarikçi şirketler.

```sql
CREATE TABLE Supplier (
    Id   INTEGER PRIMARY KEY,
    Name TEXT NOT NULL
);
```

---

### Supplier_Product
Bir tedarikçinin hangi raw material'ları sağlayabildiğini belirtir. Çoka-çok ilişki.

```sql
CREATE TABLE Supplier_Product (
    SupplierId INTEGER NOT NULL,
    ProductId  INTEGER NOT NULL,
    PRIMARY KEY (SupplierId, ProductId),
    FOREIGN KEY (SupplierId) REFERENCES Supplier(Id),
    FOREIGN KEY (ProductId)  REFERENCES Product(Id)
);
```

---

## İlişki Diyagramı

```
Company
  │
  ├─── Product (CompanyId)
  │      │
  │      ├─── Product_FinishedGood (ProductId)
  │      │
  │      └─── Product_RawMaterial (ProductId, CompanyId → Company)
  │
  └─── (Product_RawMaterial.CompanyId)

Product (FG)
  └─── BOM (ProducedProductId)
         └─── BOM_Component (BOMId)
                └─── Product (RM) via ConsumedProductId
                       └─── Supplier_Product (ProductId)
                              └─── Supplier
```

---

## Örnek Query: FG → Raw Materials → Suppliers

```sql
SELECT
    p.SKU            AS fg_sku,
    fg.Market,
    fg.MarketSearch,
    rm_p.SKU         AS rm_sku,
    rm.MaterialName,
    s.Name           AS supplier_name
FROM Product p
JOIN Product_FinishedGood fg ON fg.ProductId = p.Id
JOIN BOM b                   ON b.ProducedProductId = p.Id
JOIN BOM_Component bc        ON bc.BOMId = b.Id
JOIN Product rm_p            ON rm_p.Id = bc.ConsumedProductId
JOIN Product_RawMaterial rm  ON rm.ProductId = rm_p.Id
LEFT JOIN Supplier_Product sp ON sp.ProductId = rm_p.Id
LEFT JOIN Supplier s          ON s.Id = sp.SupplierId
ORDER BY p.Id, rm_p.Id, s.Name;
```

---

## Scripts

| Script | Açıklama |
|---|---|
| `raw_material_parser.py` | `Product` → `Product_RawMaterial` tablosunu doldurur |
| `finished_good_parser.py` | `Product` → `Product_FinishedGood` tablosunu doldurur |
| `bom_query.py` | Her FG için RM listesini JSON olarak üretir. `--with-suppliers` flag'i ile supplier'lar da dahil edilir |
| `material_query.py` | Her RM için supplier ve kullanıldığı FG listesini JSON olarak üretir. |
