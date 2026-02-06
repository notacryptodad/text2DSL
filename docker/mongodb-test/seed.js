// MongoDB seed data for test database
// Auto-runs on container initialization via docker-entrypoint-initdb.d

print("Seeding MongoDB test database...");

db = db.getSiblingDB('text2x_test');

// Drop existing collections for clean seeding
db.customers.drop();
db.products.drop();
db.orders.drop();
db.order_items.drop();
db.users.drop();

// Create collections with validation
db.createCollection('customers', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['name', 'email'],
            properties: {
                name: { bsonType: 'string' },
                email: { bsonType: 'string' },
                phone: { bsonType: 'string' },
                address: { bsonType: 'string' },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('products', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['name', 'price'],
            properties: {
                name: { bsonType: 'string' },
                description: { bsonType: 'string' },
                price: { bsonType: 'number' },
                category: { bsonType: 'string' },
                in_stock: { bsonType: 'bool' },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('orders', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['customer_id', 'total', 'status'],
            properties: {
                customer_id: { bsonType: 'objectId' },
                total: { bsonType: 'number' },
                status: { bsonType: 'string', enum: ['pending', 'completed', 'shipped', 'cancelled'] },
                shipping_address: { bsonType: 'string' },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('order_items', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['order_id', 'product_id', 'quantity', 'unit_price'],
            properties: {
                order_id: { bsonType: 'objectId' },
                product_id: { bsonType: 'objectId' },
                quantity: { bsonType: 'int' },
                unit_price: { bsonType: 'number' }
            }
        }
    }
});

db.createCollection('users', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['username', 'email'],
            properties: {
                username: { bsonType: 'string' },
                email: { bsonType: 'string' },
                role: { bsonType: 'string', enum: ['admin', 'user', 'guest'] },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

// Seed customers
db.customers.insertMany([
    { name: 'Alice Johnson', email: 'alice@example.com', phone: '+1-555-0101', address: '123 Main St, City A', created_at: new Date('2024-01-15') },
    { name: 'Bob Smith', email: 'bob@example.com', phone: '+1-555-0102', address: '456 Oak Ave, City B', created_at: new Date('2024-02-20') },
    { name: 'Carol Williams', email: 'carol@example.com', phone: '+1-555-0103', address: '789 Pine Rd, City C', created_at: new Date('2024-03-10') },
    { name: 'David Brown', email: 'david@example.com', phone: '+1-555-0104', address: '321 Elm St, City D', created_at: new Date('2024-04-05') },
    { name: 'Eva Martinez', email: 'eva@example.com', phone: '+1-555-0105', address: '654 Maple Dr, City E', created_at: new Date('2024-05-01') }
]);

// Seed products
db.products.insertMany([
    { name: 'Laptop Pro 15', description: 'High-performance laptop with 16GB RAM', price: 1299.99, category: 'Electronics', in_stock: true, created_at: new Date('2024-01-01') },
    { name: 'Wireless Mouse', description: 'Ergonomic wireless mouse', price: 29.99, category: 'Electronics', in_stock: true, created_at: new Date('2024-01-15') },
    { name: 'USB-C Hub', description: '7-in-1 USB-C hub with HDMI', price: 49.99, category: 'Electronics', in_stock: true, created_at: new Date('2024-02-01') },
    { name: 'Running Shoes', description: 'Lightweight running shoes', price: 129.99, category: 'Sports', in_stock: true, created_at: new Date('2024-02-15') },
    { name: 'Yoga Mat', description: 'Non-slip yoga mat', price: 34.99, category: 'Sports', in_stock: true, created_at: new Date('2024-03-01') },
    { name: 'Coffee Maker', description: 'Automatic coffee maker', price: 89.99, category: 'Home', in_stock: true, created_at: new Date('2024-03-15') },
    { name: 'Blender', description: 'High-speed blender', price: 69.99, category: 'Home', in_stock: true, created_at: new Date('2024-04-01') },
    { name: 'Air Fryer', description: 'Digital air fryer 5L', price: 99.99, category: 'Home', in_stock: false, created_at: new Date('2024-04-15') }
]);

// Get product ObjectIds for order items
const products = db.products.find().toArray();
const productIds = {};
products.forEach(p => productIds[p.name] = p._id);

// Get customer ObjectIds
const customers = db.customers.find().toArray();
const customerIds = {};
customers.forEach(c => customerIds[c.name] = c._id);

// Seed orders
db.orders.insertMany([
    { customer_id: customerIds['Alice Johnson'], total: 1329.98, status: 'completed', shipping_address: '123 Main St, City A', created_at: new Date('2024-06-01') },
    { customer_id: customerIds['Bob Smith'], total: 164.98, status: 'completed', shipping_address: '456 Oak Ave, City B', created_at: new Date('2024-06-15') },
    { customer_id: customerIds['Carol Williams'], total: 89.99, status: 'pending', shipping_address: '789 Pine Rd, City C', created_at: new Date('2024-07-01') },
    { customer_id: customerIds['Alice Johnson'], total: 99.99, status: 'shipped', shipping_address: '123 Main St, City A', created_at: new Date('2024-07-15') },
    { customer_id: customerIds['David Brown'], total: 29.99, status: 'completed', shipping_address: '321 Elm St, City D', created_at: new Date('2024-08-01') }
]);

// Get order ObjectIds
const orders = db.orders.find().toArray();
const orderIds = {};
orders.forEach(o => orderIds[o.customer_id.toString()] = o._id);

// Seed order items
db.order_items.insertMany([
    { order_id: orderIds[customerIds['Alice Johnson'].toString()], product_id: productIds['Laptop Pro 15'], quantity: 1, unit_price: 1299.99 },
    { order_id: orderIds[customerIds['Alice Johnson'].toString()], product_id: productIds['Wireless Mouse'], quantity: 1, unit_price: 29.99 },
    { order_id: orderIds[customerIds['Bob Smith'].toString()], product_id: productIds['Running Shoes'], quantity: 1, unit_price: 129.99 },
    { order_id: orderIds[customerIds['Bob Smith'].toString()], product_id: productIds['Yoga Mat'], quantity: 1, unit_price: 34.99 },
    { order_id: orderIds[customerIds['Carol Williams'].toString()], product_id: productIds['Coffee Maker'], quantity: 1, unit_price: 89.99 },
    { order_id: orderIds[customerIds['Alice Johnson'].toString()], product_id: productIds['Air Fryer'], quantity: 1, unit_price: 99.99 },
    { order_id: orderIds[customerIds['David Brown'].toString()], product_id: productIds['Wireless Mouse'], quantity: 1, unit_price: 29.99 }
]);

// Seed users
db.users.insertMany([
    { username: 'admin', email: 'admin@example.com', role: 'admin', created_at: new Date('2024-01-01') },
    { username: 'alice', email: 'alice@example.com', role: 'user', created_at: new Date('2024-01-15') },
    { username: 'bob', email: 'bob@example.com', role: 'user', created_at: new Date('2024-02-20') },
    { username: 'carol', email: 'carol@example.com', role: 'user', created_at: new Date('2024-03-10') },
    { username: 'guest', email: 'guest@example.com', role: 'guest', created_at: new Date('2024-04-01') }
]);

// Create indexes
db.customers.createIndex({ email: 1 }, { unique: true });
db.products.createIndex({ category: 1 });
db.products.createIndex({ in_stock: 1 });
db.orders.createIndex({ customer_id: 1 });
db.orders.createIndex({ status: 1 });
db.order_items.createIndex({ order_id: 1 });
db.order_items.createIndex({ product_id: 1 });
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });

// Print summary
print("MongoDB seed completed!");
print("Collections created: " + db.getCollectionNames().join(', '));
print("Documents seeded:");
print("  customers: " + db.customers.countDocuments());
print("  products: " + db.products.countDocuments());
print("  orders: " + db.orders.countDocuments());
print("  order_items: " + db.order_items.countDocuments());
print("  users: " + db.users.countDocuments());
