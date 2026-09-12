-- Top 10 customers by total amount spent.
SELECT
    c.CompanyName                                                  AS customer,
    c.Country                                                      AS country,
    COUNT(DISTINCT o.OrderID)                                      AS orders,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS total_spent
FROM Customers AS c
JOIN Orders AS o           ON o.CustomerID = c.CustomerID
JOIN "Order Details" AS od ON od.OrderID = o.OrderID
GROUP BY c.CustomerID
ORDER BY total_spent DESC
LIMIT 10;
