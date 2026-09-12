-- Revenue and units sold per product category, with each category's share of total revenue.
WITH category_sales AS (
    SELECT
        cat.CategoryName                                           AS category,
        SUM(od.Quantity)                                           AS units_sold,
        SUM(od.UnitPrice * od.Quantity * (1 - od.Discount))        AS revenue
    FROM "Order Details" AS od
    JOIN Products AS p     ON p.ProductID = od.ProductID
    JOIN Categories AS cat ON cat.CategoryID = p.CategoryID
    GROUP BY cat.CategoryID
)
SELECT
    category,
    units_sold,
    ROUND(revenue, 2)                                  AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)   AS revenue_share_pct
FROM category_sales
ORDER BY revenue DESC;
