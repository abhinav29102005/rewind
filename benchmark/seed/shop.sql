-- Sample shop seed schema and data for benchmark scenarios
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    balance REAL NOT NULL DEFAULT 100.0
);

INSERT INTO users (id, username, email, role, balance) VALUES
(1, 'alice', 'alice@example.com', 'admin', 500.0),
(2, 'bob', 'bob@example.com', 'customer', 50.0),
(3, 'charlie', 'charlie@example.com', 'customer', 120.0),
(4, 'david', 'david@example.com', 'customer', 30.0),
(5, 'eve', 'eve@example.com', 'customer', 200.0);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    total REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed'
);

INSERT INTO orders (id, user_id, total, status) VALUES
(101, 1, 45.0, 'completed'),
(102, 2, 90.0, 'completed'),
(103, 3, 15.0, 'pending'),
(104, 4, 30.0, 'completed'),
(105, 5, 120.0, 'completed'),
(106, 2, 25.0, 'completed');
