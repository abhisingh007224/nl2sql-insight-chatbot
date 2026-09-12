-- Active (not discontinued) products whose stock is at or below the reorder level.
SELECT
    p.ProductName      AS product,
    cat.CategoryName   AS category,
    p.UnitsInStock     AS units_in_stock,
    p.ReorderLevel     AS reorder_level,
    p.UnitsOnOrder     AS units_on_order,
    s.CompanyName      AS supplier
FROM Products AS p
JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
JOIN Suppliers AS s    ON s.SupplierID = p.SupplierID
WHERE CAST(p.Discontinued AS INTEGER) = 0
  AND p.UnitsInStock <= p.ReorderLevel
ORDER BY p.UnitsInStock ASC;
