-- Test schema for Text2DSL MVP
-- Simple e-commerce schema for demonstration

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert sample data
INSERT INTO customers (name, email) VALUES
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com'),
    ('Bob Johnson', 'bob@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (name, price, category, stock_quantity) VALUES
    ('Laptop', 999.99, 'Electronics', 50),
    ('Mouse', 29.99, 'Electronics', 200),
    ('Desk Chair', 199.99, 'Furniture', 30),
    ('Notebook', 5.99, 'Office Supplies', 500),
    ('Monitor', 299.99, 'Electronics', 75)
ON CONFLICT DO NOTHING;

INSERT INTO orders (customer_id, total_amount, status, created_at) VALUES
    (1, 1299.98, 'completed', NOW() - INTERVAL '45 days'),
    (2, 199.99, 'shipped', NOW() - INTERVAL '15 days'),
    (1, 35.98, 'pending', NOW() - INTERVAL '2 days'),
    (3, 1599.95, 'completed', NOW() - INTERVAL '30 days')
ON CONFLICT DO NOTHING;
