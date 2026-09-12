-- Number of customers registered in each country.
SELECT
    c.Country    AS country,
    COUNT(*)     AS customers
FROM Customers AS c
GROUP BY c.Country
ORDER BY customers DESC, country;
