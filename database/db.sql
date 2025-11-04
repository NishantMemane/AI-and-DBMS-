-- Create database and use it
-- CREATE DATABASE personal_finance_tracker;
GO
USE personal_finance_tracker;
GO

-- 1. USERS TABLE
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    password NVARCHAR(100) NOT NULL,   -- plain text as requested
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- 2. INCOME TABLE
CREATE TABLE income (
    income_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    source NVARCHAR(100) NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    date DATE NOT NULL,
    category NVARCHAR(50) NULL,
    notes NVARCHAR(MAX) NULL,
    CONSTRAINT FK_income_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
GO

-- 3. EXPENSES TABLE
CREATE TABLE expenses (
    expense_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    category NVARCHAR(50) NOT NULL,
    description NVARCHAR(MAX) NULL,
    amount DECIMAL(18,2) NOT NULL,
    date DATE NOT NULL,
    payment_method NVARCHAR(50) NULL,
    CONSTRAINT FK_expenses_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
GO

-- 4. TRANSACTIONS TABLE
CREATE TABLE transactions (
    transaction_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    type NVARCHAR(10) NOT NULL,  -- 'income' or 'expense'
    category NVARCHAR(50) NULL,
    description NVARCHAR(MAX) NULL,
    amount DECIMAL(18,2) NOT NULL,
    date DATE NOT NULL,
    CONSTRAINT CHK_transactions_type CHECK (type IN ('income','expense')),
    CONSTRAINT FK_transactions_users FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
GO

-- ✅ Example inserts
INSERT INTO users (name, email, password) VALUES
('Shree Memane','shree@gmail.com','12345');
GO

INSERT INTO income (user_id, source, amount, date, category, notes) VALUES
(1, 'Job Salary', 25000.00, '2025-10-14', 'Work', 'October salary'),
(1, 'Freelance Project', 8000.00, '2025-10-10', 'Freelance', 'Logo design project');
GO

INSERT INTO expenses (user_id, category, description, amount, date, payment_method) VALUES
(1, 'Food', 'Dinner at restaurant', 500.00, '2025-10-13', 'Cash'),
(1, 'Bills', 'Electricity bill', 1200.00, '2025-10-12', 'UPI');
GO

INSERT INTO transactions (user_id, type, category, description, amount, date) VALUES
(1, 'income', 'Work', 'Job Salary', 25000.00, '2025-10-14'),
(1, 'expense', 'Food', 'Dinner at restaurant', 500.00, '2025-10-13'),
(1, 'expense', 'Bills', 'Electricity bill', 1200.00, '2025-10-12');
GO
