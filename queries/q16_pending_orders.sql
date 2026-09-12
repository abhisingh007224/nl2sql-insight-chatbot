-- Orders that have not been shipped yet.
SELECT
    o.OrderID                     AS order_id,
    c.CompanyName                 AS customer,
    date(o.OrderDate)             AS order_date,
    date(o.RequiredDate)          AS required_date,
    o.ShipCountry                 AS ship_country
FROM Orders AS o
JOIN Customers AS c ON c.CustomerID = o.CustomerID
WHERE o.ShippedDate IS NULL
ORDER BY o.OrderDate;
