-- Overview of every table in the database: number of rows and number of columns, plus a total line.
WITH row_counts(table_name, row_count) AS (
    SELECT 'Categories', COUNT(*) FROM Categories
    UNION ALL SELECT 'CustomerCustomerDemo', COUNT(*) FROM CustomerCustomerDemo
    UNION ALL SELECT 'CustomerDemographics', COUNT(*) FROM CustomerDemographics
    UNION ALL SELECT 'Customers', COUNT(*) FROM Customers
    UNION ALL SELECT 'EmployeeTerritories', COUNT(*) FROM EmployeeTerritories
    UNION ALL SELECT 'Employees', COUNT(*) FROM Employees
    UNION ALL SELECT 'Order Details', COUNT(*) FROM "Order Details"
    UNION ALL SELECT 'Orders', COUNT(*) FROM Orders
    UNION ALL SELECT 'Products', COUNT(*) FROM Products
    UNION ALL SELECT 'Regions', COUNT(*) FROM Regions
    UNION ALL SELECT 'Shippers', COUNT(*) FROM Shippers
    UNION ALL SELECT 'Suppliers', COUNT(*) FROM Suppliers
    UNION ALL SELECT 'Territories', COUNT(*) FROM Territories
),
per_table AS (
    SELECT
        r.table_name,
        r.row_count,
        (SELECT COUNT(*) FROM pragma_table_info(r.table_name)) AS column_count
    FROM row_counts AS r
)
SELECT table_name, row_count, column_count
FROM (
    SELECT table_name, row_count, column_count, 0 AS sort_group FROM per_table
    UNION ALL
    SELECT 'TOTAL (13 tables)', SUM(row_count), SUM(column_count), 1 FROM per_table
)
ORDER BY sort_group, row_count DESC;
