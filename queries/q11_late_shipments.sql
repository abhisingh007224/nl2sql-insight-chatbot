-- How many shipped orders arrived after their required date, and by how much on average.
SELECT
    COUNT(*)                                                               AS shipped_orders,
    SUM(o.ShippedDate > o.RequiredDate)                                    AS late_orders,
    ROUND(100.0 * SUM(o.ShippedDate > o.RequiredDate) / COUNT(*), 2)       AS late_pct,
    ROUND(AVG(CASE WHEN o.ShippedDate > o.RequiredDate
                   THEN julianday(o.ShippedDate) - julianday(o.RequiredDate) END), 2)
                                                                           AS avg_days_late
FROM Orders AS o
WHERE o.ShippedDate IS NOT NULL;
