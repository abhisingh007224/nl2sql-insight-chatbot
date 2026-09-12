-- Impact of discounts: gross revenue before discounts, total discount given,
-- net revenue and the share of order lines that received a discount.
SELECT
    ROUND(SUM(od.UnitPrice * od.Quantity), 2)                          AS gross_revenue,
    ROUND(SUM(od.UnitPrice * od.Quantity * od.Discount), 2)            AS total_discount_given,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)      AS net_revenue,
    ROUND(100.0 * SUM(od.Discount > 0) / COUNT(*), 2)                  AS discounted_lines_pct
FROM "Order Details" AS od;
