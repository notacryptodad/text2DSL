#!/bin/bash
# Seed test PostgreSQL with e-commerce schema and data
# Usage: ./seed.sh [container] [user] [database]

CONTAINER=${1:-text2dsl-postgres-test}
USER=${2:-text2x}
DB=${3:-text2x}

docker exec -i $CONTAINER psql -U $USER -d $DB << 'EOF'
-- E-commerce schema
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    in_stock BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Seed data
TRUNCATE customers, products, orders, order_items RESTART IDENTITY CASCADE;

INSERT INTO customers (name, email) VALUES
('Alice Johnson', 'alice@example.com'),
('Bob Smith', 'bob@example.com'),
('Carol Williams', 'carol@example.com'),
('David Brown', 'david@example.com'),
('Eva Martinez', 'eva@example.com');

INSERT INTO products (name, description, price, category, in_stock) VALUES
('Laptop Pro 15', 'High-performance laptop with 16GB RAM', 1299.99, 'Electronics', true),
('Wireless Mouse', 'Ergonomic wireless mouse', 29.99, 'Electronics', true),
('USB-C Hub', '7-in-1 USB-C hub with HDMI', 49.99, 'Electronics', true),
('Running Shoes', 'Lightweight running shoes', 129.99, 'Sports', true),
('Yoga Mat', 'Non-slip yoga mat', 34.99, 'Sports', true),
('Coffee Maker', 'Automatic coffee maker', 89.99, 'Home', true),
('Blender', 'High-speed blender', 69.99, 'Home', true),
('Air Fryer', 'Digital air fryer 5L', 99.99, 'Home', false);

INSERT INTO orders (customer_id, total, status) VALUES
(1, 1329.98, 'completed'),
(2, 164.98, 'completed'),
(3, 89.99, 'pending'),
(1, 99.99, 'shipped'),
(4, 29.99, 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 1299.99),
(1, 2, 1, 29.99),
(2, 4, 1, 129.99),
(2, 5, 1, 34.99),
(3, 6, 1, 89.99),
(4, 8, 1, 99.99),
(5, 2, 1, 29.99);

SELECT 'Seeded: ' || count(*) || ' customers' FROM customers;
SELECT 'Seeded: ' || count(*) || ' products' FROM products;
SELECT 'Seeded: ' || count(*) || ' orders' FROM orders;
SELECT 'Seeded: ' || count(*) || ' order_items' FROM order_items;
EOF
