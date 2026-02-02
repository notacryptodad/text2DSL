-- Seed data for text2DSL testing

-- Customers (20)
INSERT INTO customers (name, email) VALUES
('Alice Johnson', 'alice@example.com'),
('Bob Smith', 'bob@example.com'),
('Carol Williams', 'carol@example.com'),
('David Brown', 'david@example.com'),
('Eva Martinez', 'eva@example.com'),
('Frank Garcia', 'frank@example.com'),
('Grace Lee', 'grace@example.com'),
('Henry Wilson', 'henry@example.com'),
('Ivy Chen', 'ivy@example.com'),
('Jack Taylor', 'jack@example.com'),
('Karen Anderson', 'karen@example.com'),
('Leo Thomas', 'leo@example.com'),
('Maria Jackson', 'maria@example.com'),
('Nathan White', 'nathan@example.com'),
('Olivia Harris', 'olivia@example.com'),
('Peter Martin', 'peter@example.com'),
('Quinn Thompson', 'quinn@example.com'),
('Rachel Moore', 'rachel@example.com'),
('Sam Davis', 'sam@example.com'),
('Tina Miller', 'tina@example.com');

-- Products (50)
INSERT INTO products (name, description, price, category, in_stock) VALUES
('Laptop Pro 15', 'High-performance laptop with 16GB RAM', 1299.99, 'Electronics', true),
('Wireless Mouse', 'Ergonomic wireless mouse', 29.99, 'Electronics', true),
('USB-C Hub', '7-in-1 USB-C hub with HDMI', 49.99, 'Electronics', true),
('Mechanical Keyboard', 'RGB mechanical keyboard', 89.99, 'Electronics', true),
('Monitor 27"', '4K IPS monitor', 399.99, 'Electronics', true),
('Webcam HD', '1080p webcam with mic', 79.99, 'Electronics', true),
('Headphones Pro', 'Noise-canceling headphones', 249.99, 'Electronics', true),
('Tablet 10"', '10-inch tablet with stylus', 449.99, 'Electronics', true),
('Smart Watch', 'Fitness tracking smart watch', 199.99, 'Electronics', true),
('Bluetooth Speaker', 'Portable bluetooth speaker', 59.99, 'Electronics', true),
('Running Shoes', 'Lightweight running shoes', 129.99, 'Sports', true),
('Yoga Mat', 'Non-slip yoga mat', 34.99, 'Sports', true),
('Dumbbells Set', '20lb dumbbells pair', 79.99, 'Sports', true),
('Tennis Racket', 'Professional tennis racket', 149.99, 'Sports', true),
('Basketball', 'Official size basketball', 29.99, 'Sports', true),
('Soccer Ball', 'FIFA approved soccer ball', 39.99, 'Sports', true),
('Bicycle Helmet', 'Safety bicycle helmet', 49.99, 'Sports', true),
('Swim Goggles', 'Anti-fog swim goggles', 19.99, 'Sports', true),
('Golf Clubs Set', 'Complete golf clubs set', 599.99, 'Sports', false),
('Camping Tent', '4-person camping tent', 199.99, 'Sports', true),
('Coffee Maker', 'Automatic coffee maker', 89.99, 'Home', true),
('Blender', 'High-speed blender', 69.99, 'Home', true),
('Air Fryer', 'Digital air fryer 5L', 99.99, 'Home', true),
('Vacuum Cleaner', 'Cordless vacuum cleaner', 299.99, 'Home', true),
('Rice Cooker', '10-cup rice cooker', 49.99, 'Home', true),
('Toaster', '4-slice toaster', 39.99, 'Home', true),
('Microwave', 'Compact microwave oven', 89.99, 'Home', true),
('Stand Mixer', 'Professional stand mixer', 349.99, 'Home', true),
('Food Processor', 'Multi-function food processor', 129.99, 'Home', true),
('Electric Kettle', 'Fast boil electric kettle', 34.99, 'Home', true),
('T-Shirt Basic', '100% cotton t-shirt', 19.99, 'Clothing', true),
('Jeans Classic', 'Classic fit jeans', 59.99, 'Clothing', true),
('Winter Jacket', 'Warm winter jacket', 149.99, 'Clothing', true),
('Sneakers', 'Casual sneakers', 79.99, 'Clothing', true),
('Dress Shirt', 'Formal dress shirt', 49.99, 'Clothing', true),
('Hoodie', 'Fleece pullover hoodie', 44.99, 'Clothing', true),
('Shorts', 'Athletic shorts', 29.99, 'Clothing', true),
('Socks Pack', '6-pair socks pack', 14.99, 'Clothing', true),
('Belt Leather', 'Genuine leather belt', 34.99, 'Clothing', true),
('Cap', 'Adjustable baseball cap', 24.99, 'Clothing', true),
('Novel Bestseller', 'Top fiction novel', 14.99, 'Books', true),
('Cookbook', 'International recipes cookbook', 29.99, 'Books', true),
('Tech Guide', 'Programming guide book', 49.99, 'Books', true),
('Biography', 'Inspiring biography', 24.99, 'Books', true),
('Art Book', 'Modern art collection', 39.99, 'Books', true),
('Science Book', 'Popular science book', 19.99, 'Books', true),
('History Book', 'World history overview', 34.99, 'Books', true),
('Self Help', 'Personal development book', 16.99, 'Books', true),
('Travel Guide', 'Europe travel guide', 22.99, 'Books', true),
('Dictionary', 'Comprehensive dictionary', 29.99, 'Books', true);

-- Orders (100)
INSERT INTO orders (customer_id, total, status, created_at) 
SELECT 
    (random() * 19 + 1)::int,
    (random() * 500 + 20)::decimal(10,2),
    (ARRAY['pending', 'processing', 'shipped', 'delivered', 'cancelled'])[floor(random() * 5 + 1)::int],
    NOW() - (random() * 90 || ' days')::interval
FROM generate_series(1, 100);

-- Order Items (200+)
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT 
    (random() * 99 + 1)::int,
    p.id,
    (random() * 3 + 1)::int,
    p.price
FROM generate_series(1, 200), products p
WHERE p.id = (random() * 49 + 1)::int
LIMIT 200;
