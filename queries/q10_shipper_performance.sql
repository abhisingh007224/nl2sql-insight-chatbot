-- Shipping company comparison: orders shipped, average freight cost,
-- average days from order to shipment and share of late shipments.
SELECT
    s.CompanyName                                                          AS shipper,
    COUNT(*)                                                               AS orders_shipped,
    ROUND(AVG(o.Freight), 2)                                               AS avg_freight,
    ROUND(AVG(julianday(o.ShippedDate) - julianday(o.OrderDate)), 2)       AS avg_days_to_ship,
    ROUND(100.0 * SUM(o.ShippedDate > o.RequiredDate) / COUNT(*), 2)       AS late_pct
FROM Orders AS o
JOIN Shippers AS s ON s.ShipperID = o.ShipVia
WHERE o.ShippedDate IS NOT NULL
GROUP BY s.ShipperID
ORDER BY orders_shipped DESC;
