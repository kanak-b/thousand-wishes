CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    email VARCHAR,
    location VARCHAR,
    registered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clickstream (
    user_id VARCHAR,
    session_id VARCHAR,
    timestamp TIMESTAMP,
    page VARCHAR,
    device VARCHAR,
    action VARCHAR
);

CREATE TABLE IF NOT EXISTS transactions (
    user_id VARCHAR,
    session_id VARCHAR,
    transaction_id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP,
    transaction_amount FLOAT,
    payment_method VARCHAR,
    payment_status VARCHAR,
    order_status VARCHAR,
    product_category VARCHAR,
    products TEXT
);

CREATE TABLE IF NOT EXISTS transaction_items  (
    transaction_id VARCHAR,
    product_id VARCHAR,
    product_category VARCHAR,
    quantity INT,
    unit_price FLOAT,
    product_spend FLOAT,
    timestamp TIMESTAMP
);

