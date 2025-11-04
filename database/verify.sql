CREATE VIEW financial_summary AS
SELECT 
    u.user_id,
    u.name,
    ISNULL(SUM(CASE WHEN t.type = 'income' THEN t.amount END), 0) AS total_income,
    ISNULL(SUM(CASE WHEN t.type = 'expense' THEN t.amount END), 0) AS total_expenses,
    ISNULL(SUM(CASE WHEN t.type = 'income' THEN t.amount END), 0)
      - ISNULL(SUM(CASE WHEN t.type = 'expense' THEN t.amount END), 0) AS balance
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id
GROUP BY u.user_id, u.name;
GO
