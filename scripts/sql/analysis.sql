-- SQLite; one row per order before joining to any item analysis.
-- Calendar-day lateness, only eligible delivered orders.
SELECT c.State, COUNT(*) AS eligible_orders, SUM(o.IsLate) AS late_orders,
       ROUND(100.0 * SUM(o.IsLate) / COUNT(*), 2) AS late_pct,
       ROUND(AVG(o.DeliveryDays), 2) AS mean_delivery_days
FROM Orders o JOIN Customers c ON c.CustomerID = o.CustomerID
WHERE o.DeliveryEligible = 1
GROUP BY c.State ORDER BY late_orders DESC;

-- Experience association; not proof that delay caused poor ratings.
SELECT DeliveryOutcome, COUNT(*) AS orders, COUNT(ReviewScore) AS reviewed,
       ROUND(AVG(ReviewScore),2) AS mean_review,
       ROUND(100.0 * SUM(CASE WHEN ReviewScore <= 2 THEN 1 ELSE 0 END)
         / NULLIF(COUNT(ReviewScore),0),2) AS low_review_pct
FROM Orders GROUP BY DeliveryOutcome;

-- Seller attribution: a multi-seller order belongs to each involved seller.
WITH seller_orders AS (SELECT DISTINCT SellerID, OrderID FROM Items)
SELECT s.SellerID, COUNT(*) AS eligible_orders, SUM(o.IsLate) AS late_orders,
       ROUND(100.0 * SUM(o.IsLate) / COUNT(*),2) AS late_pct
FROM seller_orders s JOIN Orders o ON s.OrderID=o.OrderID
WHERE o.DeliveryEligible=1
GROUP BY s.SellerID HAVING COUNT(*) >= 100 ORDER BY late_orders DESC;
