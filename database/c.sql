-- ==========================
-- Automatically rename all user_id columns to UserID
-- ==========================

DECLARE @TableName NVARCHAR(128)
DECLARE @ColumnName NVARCHAR(128)
DECLARE @SQL NVARCHAR(MAX)

-- Cursor to iterate through all tables with a column named 'user_id'
DECLARE column_cursor CURSOR FOR
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME = 'user_id'

OPEN column_cursor
FETCH NEXT FROM column_cursor INTO @TableName, @ColumnName

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @SQL = 'EXEC sp_rename ''' + @TableName + '.' + @ColumnName + ''', ''UserID'', ''COLUMN'''
    PRINT @SQL   -- Prints the command so you can review it
    EXEC sp_executesql @SQL

    FETCH NEXT FROM column_cursor INTO @TableName, @ColumnName
END

CLOSE column_cursor
DEALLOCATE column_cursor

