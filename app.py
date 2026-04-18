from flask import Flask, render_template_string, request, jsonify
import json
from db import db
from service import suggest_alternatives
from comparison_engine import compare_products, check_organic_status

app = Flask(__name__)

# HTML template with dark UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Sourcing Optimizer</title>
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
        .product-card {
            background: #2a2a2a;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            border: 1px solid #444;
        }
        .product-name {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #ffffff;
        }
        .product-info {
            color: #cccccc;
            margin-bottom: 0.5rem;
        }
        .scores {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .score-item {
            background: #333;
            padding: 0.75rem;
            border-radius: 6px;
            text-align: center;
        }
        .score-label {
            font-size: 0.875rem;
            color: #aaaaaa;
            margin-bottom: 0.25rem;
        }
        .score-value {
            font-size: 1.25rem;
            font-weight: 600;
            color: #ffffff;
        }
        .warning {
            background: #ff6b35;
            color: #ffffff;
            padding: 0.75rem;
            border-radius: 6px;
            margin-top: 1rem;
        }
        .organic-status {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        .organic-yes {
            background: #4caf50;
            color: white;
        }
        .organic-no {
            background: #f44336;
            color: white;
        }
        .no-match {
            text-align: center;
            color: #ff6b35;
            font-size: 1.25rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Sourcing Optimizer</h1>
        
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
        
        <div id="results" class="results" style="display: none;"></div>
    </div>

    <script>
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
            const resultsDiv = document.getElementById('results');
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
            const resultsDiv = document.getElementById('results');
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
            // This is a simplified check - in reality, we'd need to pass the product data
            return null; // For now, don't show organic status in alternatives
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Get all products for dropdown
    query = "SELECT DISTINCT product_id, product_name FROM raw_material_master ORDER BY product_name"
    rows = db.execute_query(query)
    products = [{"product_id": row[0], "product_name": row[1]} for row in rows]
    
    return render_template_string(HTML_TEMPLATE, products=products)

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
        # Get supplier IDs - use the first available for each product
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