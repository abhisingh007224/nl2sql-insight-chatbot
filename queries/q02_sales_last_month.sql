-- Sales for the most recent complete calendar month in the data
-- (the month before the month of the latest order).
WITH bounds AS (
    SELECT
        date(MAX(OrderDate), 'start of month', '-1 month') AS month_start,
        date(MAX(OrderDate), 'start of month')             AS month_end
    FROM Orders
)
SELECT
    strftime('%Y-%m', b.month_start)                               AS month,
    COUNT(DISTINCT o.OrderID)                                      AS orders,
    SUM(od.Quantity)                                               AS units_sold,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS total_sales
FROM bounds AS b
JOIN Orders AS o
    ON o.OrderDate >= b.month_start AND o.OrderDate < b.month_end
JOIN "Order Details" AS od
    ON od.OrderID = o.OrderID;
