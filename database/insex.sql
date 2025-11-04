-- Index for faster filtering by user/date in income table
CREATE INDEX idx_income_user_date ON income (user_id, date);

-- Index for faster filtering by user/date in expenses table
CREATE INDEX idx_expenses_user_date ON expenses (user_id, date);

-- Index for faster reports from transactions table
CREATE INDEX idx_transactions_user_date_type ON transactions (user_id, date, type);
GO
