-- Products that have been discontinued.
SELECT
    p.ProductName      AS product,
    cat.CategoryName   AS category,
    p.UnitPrice        AS unit_price,
    p.UnitsInStock     AS units_in_stock
FROM Products AS p
JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
WHERE CAST(p.Discontinued AS INTEGER) = 1
ORDER BY p.ProductName;
