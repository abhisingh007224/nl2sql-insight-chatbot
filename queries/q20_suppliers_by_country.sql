-- Number of suppliers and products supplied, per supplier country.
SELECT
    s.Country                        AS country,
    COUNT(DISTINCT s.SupplierID)     AS suppliers,
    COUNT(p.ProductID)               AS products_supplied
FROM Suppliers AS s
LEFT JOIN Products AS p ON p.SupplierID = s.SupplierID
GROUP BY s.Country
ORDER BY suppliers DESC, products_supplied DESC;
