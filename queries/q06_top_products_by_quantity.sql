-- Top 10 best-selling products by number of units sold.
SELECT
    p.ProductName                AS product,
    cat.CategoryName             AS category,
    SUM(od.Quantity)             AS units_sold,
    COUNT(DISTINCT od.OrderID)   AS orders_containing_product
FROM "Order Details" AS od
JOIN Products AS p     ON p.ProductID = od.ProductID
JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
GROUP BY p.ProductID
ORDER BY units_sold DESC
LIMIT 10;
