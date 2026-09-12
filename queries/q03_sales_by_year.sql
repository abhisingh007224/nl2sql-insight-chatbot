-- Yearly sales trend: orders and revenue per calendar year.
SELECT
    strftime('%Y', o.OrderDate)                                    AS year,
    COUNT(DISTINCT o.OrderID)                                      AS orders,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS revenue
FROM Orders AS o
JOIN "Order Details" AS od ON od.OrderID = o.OrderID
GROUP BY year
ORDER BY year;
