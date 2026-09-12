-- The 10 products with the highest list unit price.
SELECT
    p.ProductName      AS product,
    cat.CategoryName   AS category,
    p.UnitPrice        AS unit_price,
    s.CompanyName      AS supplier
FROM Products AS p
JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
JOIN Suppliers AS s    ON s.SupplierID = p.SupplierID
ORDER BY p.UnitPrice DESC
LIMIT 10;
