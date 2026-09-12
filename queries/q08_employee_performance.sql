-- Sales performance of each employee: orders handled and revenue generated.
SELECT
    e.FirstName || ' ' || e.LastName                               AS employee,
    e.Title                                                        AS title,
    COUNT(DISTINCT o.OrderID)                                      AS orders_handled,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2)  AS revenue
FROM Employees AS e
JOIN Orders AS o           ON o.EmployeeID = e.EmployeeID
JOIN "Order Details" AS od ON od.OrderID = o.OrderID
GROUP BY e.EmployeeID
ORDER BY revenue DESC;
