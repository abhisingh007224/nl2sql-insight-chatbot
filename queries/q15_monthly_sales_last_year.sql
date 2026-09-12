-- Month-by-month revenue for the most recent complete calendar year in the data.
WITH target AS (
    SELECT CAST(strftime('%Y', MAX(OrderDate)) AS INTEGER) - 1 AS yr
    FROM Orders
)
SELECT
    strftime('%Y-%m', o.OrderDate)                                 AS month,
    COUNT(DISTINCT o.OrderID)                                      AS orders,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS revenue
FROM Orders AS o
JOIN "Order Details" AS od ON od.OrderID = o.OrderID
JOIN target AS t           ON CAST(strftime('%Y', o.OrderDate) AS INTEGER) = t.yr
GROUP BY month
ORDER BY month;
