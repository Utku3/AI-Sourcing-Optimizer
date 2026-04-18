from flask import Flask, render_template_string, request, jsonify
import json
from db import db
from service import suggest_alternatives
from comparison_engine import compare_products, check_organic_status
from enrich_raw_materials import start_watcher

app = Flask(__name__)
start_watcher(interval_seconds=60)

# HTML template with dark UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YumYum Camer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #ffffff;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 2rem;
            text-align: center;
        }
        .nav {
            display: flex;
            justify-content: center;
            margin-bottom: 2rem;
        }
        .nav button {
            padding: 0.75rem 1.5rem;
            background: #1a1a1a;
            color: #ffffff;
            border: 1px solid #333;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin: 0 0.5rem;
            transition: all 0.2s ease;
        }
        .nav button.active {
            background: #007acc;
            border-color: #007acc;
        }
        .nav button:hover {
            background: #2a2a2a;
        }
        .section {
            display: none;
        }
        .section.active {
            display: block;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #e5e5e5;
        }
        select {
            width: 100%;
            padding: 0.75rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            color: #ffffff;
            font-size: 1rem;
        }
        select:focus {
            outline: none;
            border-color: #007acc;
            box-shadow: 0 0 0 2px rgba(0, 122, 204, 0.2);
        }
        .buttons {
            display: flex;
            gap: 1rem;
            margin-top: 2rem;
        }
        button {
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, #007acc, #005999);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        button:hover {
            background: linear-gradient(135deg, #005999, #004477);
            transform: translateY(-1px);
        }
        button:disabled {
            background: #333;
            cursor: not-allowed;
            transform: none;
        }
        .results {
            margin-top: 3rem;
            padding: 2rem;
            background: #1a1a1a;
            border-radius: 12px;
            border: 1px solid #333;
        }
        .material-card {
            background: #2a2a2a;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            border: 1px solid #444;
        }
        .material-name {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #ffffff;
        }
        .finished-products {
            margin-bottom: 1rem;
        }
        .finished-products h4 {
            color: #cccccc;
            margin-bottom: 0.5rem;
        }
        .product-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .product-tag {
            background: #333;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            color: #aaaaaa;
        }
        .suppliers {
            margin-bottom: 1rem;
        }
        .suppliers h4 {
            color: #cccccc;
            margin-bottom: 0.5rem;
        }
        .supplier-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        .supplier-card {
            background: #333;
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid #444;
        }
        .supplier-name {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #ffffff;
        }
        .comparison-scores {
            font-size: 0.875rem;
            color: #cccccc;
        }
        .score-item {
            margin-bottom: 0.25rem;
        }
        .no-data {
            text-align: center;
            color: #ff6b35;
            font-size: 1.25rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YumYum Camer</h1>
        
        <div class="nav">
            <button id="companiesTab" class="active">Companies</button>
            <button id="suppliersTab">Suppliers</button>
        </div>
        
        <div id="companiesSection" class="section active">
            <div class="form-group">
                <label for="companySelect">Select Company</label>
                <select id="companySelect">
                    <option value="">Choose a company...</option>
                    {% for company in companies %}
                    <option value="{{ company.id }}">{{ company.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div id="companyResults" class="results" style="display: none;"></div>
        </div>
        
        <div id="suppliersSection" class="section">
            <form id="productForm">
                <div class="form-group">
                    <label for="product1">Select Product 1 (Required)</label>
                    <select id="product1" name="product1" required>
                        <option value="">Choose a product...</option>
                        {% for product in products %}
                        <option value="{{ product.product_id }}">{{ product.product_name }}</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="product2">Select Product 2 (Optional)</label>
                    <select id="product2" name="product2">
                        <option value="">Choose a product...</option>
                        {% for product in products %}
                        <option value="{{ product.product_id }}">{{ product.product_name }}</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="buttons">
                    <button type="button" id="seeFeasibleBtn">See Feasible Products</button>
                    <button type="button" id="feasibilityBtn" disabled>Feasibility</button>
                </div>
            </form>
            
            <div id="supplierResults" class="results" style="display: none;"></div>
        </div>
    </div>

    <script>
        // Tab switching
        document.getElementById('companiesTab').addEventListener('click', function() {
            setActiveTab('companies');
        });
        document.getElementById('suppliersTab').addEventListener('click', function() {
            setActiveTab('suppliers');
        });
        
        function setActiveTab(tab) {
            document.querySelectorAll('.nav button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
            
            if (tab === 'companies') {
                document.getElementById('companiesTab').classList.add('active');
                document.getElementById('companiesSection').classList.add('active');
            } else {
                document.getElementById('suppliersTab').classList.add('active');
                document.getElementById('suppliersSection').classList.add('active');
            }
        }

        // Companies section
        document.getElementById('companySelect').addEventListener('change', function() {
            const companyId = this.value;
            if (!companyId) {
                document.getElementById('companyResults').style.display = 'none';
                return;
            }
            
            fetch('/api/company/' + companyId)
                .then(response => response.json())
                .then(data => displayCompanyResults(data))
                .catch(error => console.error('Error:', error));
        });

        function displayCompanyResults(data) {
            const resultsDiv = document.getElementById('companyResults');
            resultsDiv.style.display = 'block';
            
            if (data.materials.length === 0) {
                resultsDiv.innerHTML = '<div class="no-data">No materials found for this company.</div>';
                return;
            }
            
            let html = '<h2>Materials Supplied by ' + data.company_name + '</h2>';
            
            data.materials.forEach(material => {
                html += '<div class="material-card">';
                html += '<div class="material-name">' + material.product_name + '</div>';
                
                if (material.finished_products.length > 0) {
                    html += '<div class="finished-products">';
                    html += '<h4>Used in Finished Products:</h4>';
                    html += '<div class="product-list">';
                    material.finished_products.forEach(product => {
                        html += '<span class="product-tag">Product ' + product + '</span>';
                    });
                    html += '</div>';
                    html += '</div>';
                }
                
                if (material.suppliers.length > 0) {
                    html += '<div class="suppliers">';
                    html += '<h4>Available Suppliers:</h4>';
                    html += '<div class="supplier-list">';
                    material.suppliers.forEach(supplier => {
                        html += '<div class="supplier-card">';
                        html += '<div class="supplier-name">' + supplier.name + ' (ID: ' + supplier.id + ')</div>';
                        if (supplier.comparisons && supplier.comparisons.length > 0) {
                            html += '<div class="comparison-scores">';
                            supplier.comparisons.forEach(comp => {
                                html += '<div class="score-item">vs ' + comp.other_supplier + ': ' + (comp.score * 100).toFixed(0) + '%</div>';
                            });
                            html += '</div>';
                        }
                        html += '</div>';
                    });
                    html += '</div>';
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            resultsDiv.innerHTML = html;
        }

        // Suppliers section (existing code)
        document.getElementById('product2').addEventListener('change', function() {
            const btn = document.getElementById('feasibilityBtn');
            btn.disabled = !this.value;
        });

        document.getElementById('seeFeasibleBtn').addEventListener('click', function() {
            const product1 = document.getElementById('product1').value;
            if (!product1) {
                alert('Please select Product 1');
                return;
            }
            
            fetch('/api/suggest/' + product1)
                .then(response => response.json())
                .then(data => displaySuggestions(data))
                .catch(error => console.error('Error:', error));
        });

        document.getElementById('feasibilityBtn').addEventListener('click', function() {
            const product1 = document.getElementById('product1').value;
            const product2 = document.getElementById('product2').value;
            if (!product1 || !product2) {
                alert('Please select both products');
                return;
            }
            
            fetch('/api/compare/' + product1 + '/' + product2)
                .then(response => response.json())
                .then(data => displayComparison(data))
                .catch(error => console.error('Error:', error));
        });

        function displaySuggestions(data) {
            const resultsDiv = document.getElementById('supplierResults');
            resultsDiv.style.display = 'block';
            
            let html = '<h2>Feasible Alternatives for ' + data.source_product.product_name + '</h2>';
            
            if (data.source_product_organic !== undefined) {
                const organicClass = data.source_product_organic ? 'organic-yes' : 'organic-no';
                const organicText = data.source_product_organic ? '✓ Organic' : '✗ Not Organic';
                html += '<div class="organic-status ' + organicClass + '">' + organicText + '</div>';
            }
            
            if (data.alternatives.length === 0) {
                html += '<p>No feasible alternatives found.</p>';
            } else {
                data.alternatives.forEach(alt => {
                    html += '<div class="product-card">';
                    html += '<div class="product-name">' + alt.product_name + '</div>';
                    
                    const organicStatus = checkOrganicStatus(alt.comparison);
                    if (organicStatus !== null) {
                        const organicClass = organicStatus ? 'organic-yes' : 'organic-no';
                        const organicText = organicStatus ? '✓ Organic' : '✗ Not Organic';
                        html += '<div class="organic-status ' + organicClass + '">' + organicText + '</div>';
                    }
                    
                    html += '<div class="scores">';
                    html += '<div class="score-item"><div class="score-label">Taste</div><div class="score-value">' + (alt.comparison.taste_score * 100).toFixed(0) + '%</div></div>';
                    html += '<div class="score-item"><div class="score-label">Feasibility</div><div class="score-value">' + (alt.comparison.feasibility_score * 100).toFixed(0) + '%</div></div>';
                    html += '<div class="score-item"><div class="score-label">Usage</div><div class="score-value">' + (alt.comparison.usage_score * 100).toFixed(0) + '%</div></div>';
                    html += '<div class="score-item"><div class="score-label">Confidence</div><div class="score-value">' + (alt.comparison.confidence_score * 100).toFixed(0) + '%</div></div>';
                    html += '<div class="score-item"><div class="score-label">Overall</div><div class="score-value">' + (alt.comparison.general_comparison_score * 100).toFixed(0) + '%</div></div>';
                    html += '</div>';
                    
                    if (alt.comparison.comparison_reason) {
                        html += '<div class="product-info">Reason: ' + alt.comparison.comparison_reason + '</div>';
                    }
                    
                    html += '</div>';
                });
            }
            
            resultsDiv.innerHTML = html;
        }

        function displayComparison(data) {
            const resultsDiv = document.getElementById('supplierResults');
            resultsDiv.style.display = 'block';
            
            if (data.general_comparison_score < 0.6) {
                resultsDiv.innerHTML = '<div class="no-match">These products don\'t match well.</div>';
                return;
            }
            
            let html = '<h2>Product Comparison</h2>';
            html += '<div class="product-card">';
            html += '<div class="product-name">Comparison Results</div>';
            html += '<div class="scores">';
            html += '<div class="score-item"><div class="score-label">Taste</div><div class="score-value">' + (data.taste_score * 100).toFixed(0) + '%</div></div>';
            html += '<div class="score-item"><div class="score-label">Feasibility</div><div class="score-value">' + (data.feasibility_score * 100).toFixed(0) + '%</div></div>';
            html += '<div class="score-item"><div class="score-label">Usage</div><div class="score-value">' + (data.usage_score * 100).toFixed(0) + '%</div></div>';
            html += '<div class="score-item"><div class="score-label">Confidence</div><div class="score-value">' + (data.confidence_score * 100).toFixed(0) + '%</div></div>';
            html += '<div class="score-item"><div class="score-label">Overall</div><div class="score-value">' + (data.general_comparison_score * 100).toFixed(0) + '%</div></div>';
            html += '</div>';
            
            if (data.comparison_reason) {
                html += '<div class="product-info">Reason: ' + data.comparison_reason + '</div>';
            }
            
            html += '</div>';
            
            resultsDiv.innerHTML = html;
        }

        function checkOrganicStatus(comparison) {
            return null;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Get companies
    companies_query = "SELECT Id, Name FROM Company ORDER BY Name"
    companies = [{"id": r[0], "name": r[1]} for r in db.execute_query(companies_query)]

    # Get products
    products_query = "SELECT DISTINCT product_id, product_name FROM raw_material_master ORDER BY product_name"
    products = [{"product_id": r[0], "product_name": r[1]} for r in db.execute_query(products_query)]
    
    return render_template_string(HTML_TEMPLATE, companies=companies, products=products)

@app.route('/api/company/<int:company_id>')
def api_company(company_id):
    try:
        # Get company name
        company_query = "SELECT Name FROM Company WHERE Id = ?"
        company_rows = db.execute_query(company_query, (company_id,))
        if not company_rows:
            return jsonify({"error": "Company not found"}), 404
        company_name = company_rows[0][0]
        
        # Get materials supplied by this company
        materials_query = "SELECT product_id, product_name FROM raw_material_master WHERE supplier_name = ?"
        materials_rows = db.execute_query(materials_query, (company_name,))
        
        materials = []
        for material_row in materials_rows:
            product_id = material_row[0]
            product_name = material_row[1]
            
            # Get finished products using this material
            finished_query = """
            SELECT DISTINCT b.ProducedProductId 
            FROM BOM_Component bc 
            JOIN BOM b ON bc.BOMId = b.Id 
            WHERE bc.ConsumedProductId = ?
            """
            finished_rows = db.execute_query(finished_query, (product_id,))
            finished_products = [row[0] for row in finished_rows]
            
            # Get all suppliers for this material
            suppliers_query = "SELECT DISTINCT supplier_id, supplier_name FROM raw_material_master WHERE product_id = ?"
            suppliers_rows = db.execute_query(suppliers_query, (product_id,))
            
            suppliers = []
            for supplier_row in suppliers_rows:
                supplier_id = supplier_row[0]
                supplier_name = supplier_row[1]
                
                # Get comparisons for this supplier vs others
                comparisons = []
                for other_supplier_row in suppliers_rows:
                    if other_supplier_row[0] != supplier_id:
                        # Try to get comparison
                        comp = db.get_comparison(product_id, supplier_id, product_id, other_supplier_row[0])
                        if comp and comp['general_comparison_score'] >= 0.6:
                            comparisons.append({
                                'other_supplier': other_supplier_row[1],
                                'score': comp['general_comparison_score']
                            })
                
                suppliers.append({
                    'id': supplier_id,
                    'name': supplier_name,
                    'comparisons': comparisons
                })
            
            materials.append({
                'product_id': product_id,
                'product_name': product_name,
                'finished_products': finished_products,
                'suppliers': suppliers
            })
        
        return jsonify({
            'company_name': company_name,
            'materials': materials
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/suggest/<int:product_id>')
def api_suggest(product_id):
    try:
        result = suggest_alternatives(product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/compare/<int:product_id_a>/<int:product_id_b>')
def api_compare(product_id_a, product_id_b):
    try:
        # Get supplier IDs
        query_a = "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1"
        rows_a = db.execute_query(query_a, (product_id_a,))
        if not rows_a:
            return jsonify({"error": f"Product {product_id_a} not found"}), 404
        supplier_id_a = rows_a[0][0]
        
        query_b = "SELECT supplier_id FROM raw_material_master WHERE product_id = ? LIMIT 1"
        rows_b = db.execute_query(query_b, (product_id_b,))
        if not rows_b:
            return jsonify({"error": f"Product {product_id_b} not found"}), 404
        supplier_id_b = rows_b[0][0]
        
        result = compare_products(product_id_a, supplier_id_a, product_id_b, supplier_id_b)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)