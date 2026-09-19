CREATE DATABASE IF NOT EXISTS querypeek_demo;
USE querypeek_demo;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL
);

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    product_id INT NOT NULL,
    employee_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    order_date DATE NOT NULL,
    CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT orders_product_fk FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT orders_employee_fk FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

INSERT INTO customers VALUES
    (1, 'Customer 1', 'Delhi', 'North'),
    (2, 'Customer 2', 'Mumbai', 'West'),
    (3, 'Customer 3', 'Bengaluru', 'South'),
    (4, 'Customer 4', 'Delhi', 'North'),
    (5, 'Customer 5', 'Kolkata', 'East'),
    (6, 'Customer 6', 'Mumbai', 'West');

INSERT INTO products VALUES
    (1, 'Analytics Pro', 'Software', 250.00),
    (2, 'Data Monitor', 'Hardware', 180.00),
    (3, 'Team Plan', 'Software', 120.00),
    (4, 'Support Package', 'Services', 300.00);

INSERT INTO employees VALUES
    (1, 'Employee 1', 'Sales'),
    (2, 'Employee 2', 'Sales'),
    (3, 'Employee 3', 'Customer Success');

INSERT INTO orders VALUES
    (1, 1, 1, 1, 500.00, '2026-01-05'),
    (2, 1, 2, 2, 180.00, '2026-01-18'),
    (3, 2, 4, 1, 600.00, '2026-02-03'),
    (4, 3, 3, 3, 240.00, '2026-02-14'),
    (5, 4, 1, 2, 750.00, '2026-02-20'),
    (6, 5, 2, 1, 360.00, '2026-03-02'),
    (7, 6, 4, 2, 900.00, '2026-03-12'),
    (8, 4, 3, 3, 360.00, '2026-03-24'),
    (9, 2, 1, 1, 250.00, '2026-04-06'),
    (10, 3, 4, 2, 600.00, '2026-04-19'),
    (11, 1, 3, 3, 240.00, '2026-05-01'),
    (12, 6, 1, 1, 500.00, '2026-05-16');

-- Run this separately with an administrator account, then use only this user in QueryPeek.
-- CREATE USER 'querypeek_readonly' IDENTIFIED BY 'replace-with-a-secret';
-- GRANT SELECT ON querypeek_demo.* TO 'querypeek_readonly';
-- FLUSH PRIVILEGES;
