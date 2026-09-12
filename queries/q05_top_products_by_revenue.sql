-- Top 10 products by revenue generated.
SELECT
    p.ProductName                                                  AS product,
    cat.CategoryName                                               AS category,
    SUM(od.Quantity)                                               AS units_sold,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS revenue
FROM "Order Details" AS od
JOIN Products AS p     ON p.ProductID = od.ProductID
JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
GROUP BY p.ProductID
ORDER BY revenue DESC
LIMIT 10;
