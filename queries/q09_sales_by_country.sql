-- Orders and revenue per shipping (destination) country.
SELECT
    o.ShipCountry                                                  AS country,
    COUNT(DISTINCT o.OrderID)                                      AS orders,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS revenue
FROM Orders AS o
JOIN "Order Details" AS od ON od.OrderID = o.OrderID
GROUP BY o.ShipCountry
ORDER BY revenue DESC;
