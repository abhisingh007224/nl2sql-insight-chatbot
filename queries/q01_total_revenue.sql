-- Total revenue, number of orders and units sold across the entire order history.
SELECT
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) AS total_revenue,
    COUNT(DISTINCT od.OrderID)                                     AS total_orders,
    SUM(od.Quantity)                                               AS units_sold
FROM "Order Details" AS od;
