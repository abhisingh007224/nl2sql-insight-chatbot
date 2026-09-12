-- Average order value, average number of distinct products and units per order, and average freight.
WITH order_totals AS (
    SELECT
        od.OrderID,
        SUM(od.UnitPrice * od.Quantity * (1 - od.Discount))  AS order_value,
        COUNT(*)                                             AS line_items,
        SUM(od.Quantity)                                     AS units
    FROM "Order Details" AS od
    GROUP BY od.OrderID
)
SELECT
    COUNT(*)                        AS orders,
    ROUND(AVG(ot.order_value), 2)   AS avg_order_value,
    ROUND(AVG(ot.line_items), 2)    AS avg_products_per_order,
    ROUND(AVG(ot.units), 2)         AS avg_units_per_order,
    ROUND(AVG(o.Freight), 2)        AS avg_freight
FROM order_totals AS ot
JOIN Orders AS o ON o.OrderID = ot.OrderID;
