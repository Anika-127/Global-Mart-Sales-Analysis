/* =====================================================================================
   RETAIL ORDERS & GLOBAL MART SALES ANALYTICS  -  SQL ANALYSIS PACK
   Table : df_orders   (created by scripts/ingest_and_clean.py or sql/01_create_table_sqlserver.sql)

   PORTABILITY NOTE
   - Written with ANSI SQL only (CTEs + window functions, no TOP / LIMIT) so the same file runs on
     SQL Server 2012+, PostgreSQL, MySQL 8+, and SQLite 3.25+.  Top-N is done with ROW_NUMBER().
   - Tested end-to-end on SQLite against the bundled dataset.
   - Money definitions:
        gross_revenue = list_price x quantity            (PRE-discount revenue)
        net_revenue   = sale_price x quantity            (POST-discount revenue)
        total_profit  = (sale_price - cost_price) x quantity
   ===================================================================================== */


-- Q01 | DATA QUALITY: row count, key nulls, date range --------------------------------
SELECT COUNT(*)                      AS total_rows,
       COUNT(DISTINCT order_id)      AS distinct_orders,
       SUM(CASE WHEN ship_mode = 'Unknown' THEN 1 ELSE 0 END) AS unknown_ship_mode_rows,
       MIN(order_date)               AS first_order_date,
       MAX(order_date)               AS last_order_date
FROM   df_orders;


-- Q02 | TOTAL ORDER VOLUME & HEADLINE KPIs ------------------------------------------
SELECT COUNT(*)                                             AS total_orders,
       SUM(quantity)                                        AS total_units,
       ROUND(SUM(gross_revenue), 2)                         AS revenue_pre_discount,
       ROUND(SUM(discount_amount), 2)                       AS total_discount_given,
       ROUND(SUM(net_revenue), 2)                           AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)                          AS total_profit,
       ROUND(100.0 * SUM(discount_amount) / SUM(gross_revenue), 2) AS discount_rate_pct,
       ROUND(100.0 * SUM(total_profit)    / SUM(net_revenue),   2) AS profit_margin_pct,
       ROUND(SUM(net_revenue) / COUNT(*), 2)                AS avg_order_value
FROM   df_orders;


-- Q03 | ORDER VOLUME + REVENUE BY YEAR (pre vs post discount) ------------------------
SELECT order_year,
       COUNT(*)                          AS orders,
       SUM(quantity)                     AS units,
       ROUND(SUM(gross_revenue), 2)      AS revenue_pre_discount,
       ROUND(SUM(net_revenue), 2)        AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)       AS total_profit,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2) AS margin_pct
FROM   df_orders
GROUP  BY order_year
ORDER  BY order_year;


-- Q04 | MONTHLY REVENUE TREND --------------------------------------------------------
SELECT order_year_month,
       COUNT(*)                     AS orders,
       ROUND(SUM(net_revenue), 2)   AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)  AS total_profit
FROM   df_orders
GROUP  BY order_year_month
ORDER  BY order_year_month;


-- Q05 | TOP 10 PRODUCTS BY POST-DISCOUNT REVENUE ---------------------------------------
WITH product_sales AS (
    SELECT product_id, category, sub_category,
           SUM(quantity)       AS units,
           SUM(net_revenue)    AS revenue,
           SUM(total_profit)   AS profit
    FROM   df_orders
    GROUP  BY product_id, category, sub_category
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rn
    FROM   product_sales
)
SELECT rn AS rank_no, product_id, category, sub_category, units,
       ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit
FROM   ranked
WHERE  rn <= 10
ORDER  BY rn;


-- Q06 | TOP 10 PRODUCTS BY PROFIT ----------------------------------------------------
WITH product_sales AS (
    SELECT product_id, category, sub_category,
           SUM(net_revenue) AS revenue, SUM(total_profit) AS profit
    FROM   df_orders
    GROUP  BY product_id, category, sub_category
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY profit DESC) AS rn
    FROM   product_sales
)
SELECT rn AS rank_no, product_id, category, sub_category,
       ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit,
       ROUND(100.0 * profit / revenue, 2) AS margin_pct
FROM   ranked
WHERE  rn <= 10
ORDER  BY rn;


-- Q07 | TOP 5 PRODUCTS IN EACH REGION (window function, partitioned) ------------------
WITH region_product AS (
    SELECT region, product_id, SUM(net_revenue) AS revenue
    FROM   df_orders
    GROUP  BY region, product_id
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY region ORDER BY revenue DESC) AS rn
    FROM   region_product
)
SELECT region, rn AS rank_no, product_id, ROUND(revenue, 2) AS revenue
FROM   ranked
WHERE  rn <= 5
ORDER  BY region, rn;


-- Q08 | REGIONAL SALES TOTALS ---------------------------------------------------------
SELECT region,
       COUNT(*)                         AS orders,
       ROUND(SUM(gross_revenue), 2)     AS revenue_pre_discount,
       ROUND(SUM(net_revenue), 2)       AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)      AS total_profit,
       ROUND(100.0 * SUM(discount_amount) / SUM(gross_revenue), 2) AS discount_rate_pct,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2)      AS margin_pct,
       ROUND(100.0 * SUM(net_revenue) / (SELECT SUM(net_revenue) FROM df_orders), 2) AS share_of_total_pct
FROM   df_orders
GROUP  BY region
ORDER  BY revenue_post_discount DESC;


-- Q09 | CITY REVENUE RANKING (top 15) ------------------------------------------------
WITH city_sales AS (
    SELECT city, state, region,
           COUNT(*) AS orders, SUM(net_revenue) AS revenue, SUM(total_profit) AS profit
    FROM   df_orders
    GROUP  BY city, state, region
), ranked AS (
    SELECT *, RANK() OVER (ORDER BY revenue DESC) AS rev_rank
    FROM   city_sales
)
SELECT rev_rank, city, state, region, orders,
       ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit,
       ROUND(100.0 * profit / revenue, 2) AS margin_pct
FROM   ranked
WHERE  rev_rank <= 15
ORDER  BY rev_rank;


-- Q10 | SEGMENT x REGION REVENUE MATRIX -----------------------------------------------
SELECT region,
       ROUND(SUM(CASE WHEN segment = 'Consumer'    THEN net_revenue ELSE 0 END), 2) AS consumer,
       ROUND(SUM(CASE WHEN segment = 'Corporate'   THEN net_revenue ELSE 0 END), 2) AS corporate,
       ROUND(SUM(CASE WHEN segment = 'Home Office' THEN net_revenue ELSE 0 END), 2) AS home_office,
       ROUND(SUM(net_revenue), 2)                                                   AS total
FROM   df_orders
GROUP  BY region
ORDER  BY total DESC;


-- Q11 | SHIP MODE PERFORMANCE --------------------------------------------------------
SELECT ship_mode,
       COUNT(*)                                          AS orders,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM df_orders), 2) AS order_share_pct,
       ROUND(SUM(net_revenue), 2)                        AS revenue_post_discount,
       ROUND(SUM(net_revenue) / COUNT(*), 2)             AS avg_order_value,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2) AS margin_pct
FROM   df_orders
GROUP  BY ship_mode
ORDER  BY orders DESC;


-- Q12 | CATEGORY: DISCOUNT RATE vs PROFIT MARGIN --------------------------------------
SELECT category,
       ROUND(SUM(gross_revenue), 2)                                AS revenue_pre_discount,
       ROUND(SUM(discount_amount), 2)                              AS discount_given,
       ROUND(100.0 * SUM(discount_amount) / SUM(gross_revenue), 2) AS discount_rate_pct,
       ROUND(SUM(net_revenue), 2)                                  AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)                                 AS total_profit,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2)      AS margin_pct
FROM   df_orders
GROUP  BY category
ORDER  BY discount_rate_pct DESC;


-- Q13 | SUB-CATEGORY: DISCOUNT RATE vs PROFIT MARGIN -----------------------------------
SELECT category, sub_category,
       ROUND(SUM(net_revenue), 2)                                  AS revenue_post_discount,
       ROUND(100.0 * SUM(discount_amount) / SUM(gross_revenue), 2) AS discount_rate_pct,
       ROUND(SUM(total_profit), 2)                                 AS total_profit,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2)      AS margin_pct
FROM   df_orders
GROUP  BY category, sub_category
ORDER  BY discount_rate_pct DESC;


-- Q14 | DISCOUNT EFFECTIVENESS: does a deeper discount buy more units or more profit? -----
SELECT discount_percent,
       COUNT(*)                                                  AS order_lines,
       ROUND(AVG(1.0 * quantity), 3)                             AS avg_units_per_line,
       ROUND(SUM(net_revenue), 2)                                AS revenue_post_discount,
       ROUND(SUM(total_profit), 2)                               AS total_profit,
       ROUND(100.0 * SUM(total_profit) / SUM(net_revenue), 2)    AS margin_pct,
       SUM(is_loss_making)                                       AS loss_making_lines
FROM   df_orders
GROUP  BY discount_percent
ORDER  BY discount_percent;


-- Q15 | LOSS-MAKING PRODUCTS (net negative profit overall) ------------------------------
SELECT product_id, category, sub_category,
       SUM(quantity)                AS units,
       ROUND(SUM(net_revenue), 2)   AS revenue,
       ROUND(SUM(total_profit), 2)  AS profit,
       ROUND(AVG(1.0 * discount_percent), 2) AS avg_discount_pct
FROM   df_orders
GROUP  BY product_id, category, sub_category
HAVING SUM(total_profit) < 0
ORDER  BY profit;


-- Q16 | MONTH-OVER-MONTH: 2022 vs 2023 (pivot with growth %) --------------------------
WITH monthly AS (
    SELECT order_month,
           SUM(CASE WHEN order_year = 2022 THEN net_revenue ELSE 0 END) AS sales_2022,
           SUM(CASE WHEN order_year = 2023 THEN net_revenue ELSE 0 END) AS sales_2023
    FROM   df_orders
    GROUP  BY order_month
)
SELECT order_month,
       ROUND(sales_2022, 2) AS sales_2022,
       ROUND(sales_2023, 2) AS sales_2023,
       ROUND(100.0 * (sales_2023 - sales_2022) / sales_2022, 2) AS yoy_growth_pct
FROM   monthly
ORDER  BY order_month;


-- Q17 | PEAK MONTH FOR EACH CATEGORY (year-month with the highest sales) ----------------
WITH cat_month AS (
    SELECT category, order_year_month, SUM(net_revenue) AS revenue
    FROM   df_orders
    GROUP  BY category, order_year_month
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rn
    FROM   cat_month
)
SELECT category, order_year_month AS peak_month, ROUND(revenue, 2) AS revenue
FROM   ranked
WHERE  rn = 1
ORDER  BY category;


-- Q18 | SUB-CATEGORY WITH THE HIGHEST PROFIT GROWTH, 2023 vs 2022 ------------------------
WITH sub_year AS (
    SELECT sub_category,
           SUM(CASE WHEN order_year = 2022 THEN total_profit ELSE 0 END) AS profit_2022,
           SUM(CASE WHEN order_year = 2023 THEN total_profit ELSE 0 END) AS profit_2023
    FROM   df_orders
    GROUP  BY sub_category
), growth AS (
    SELECT *, 100.0 * (profit_2023 - profit_2022) / profit_2022 AS growth_pct,
           ROW_NUMBER() OVER (ORDER BY (profit_2023 - profit_2022) / profit_2022 DESC) AS rn
    FROM   sub_year
)
SELECT rn AS rank_no, sub_category,
       ROUND(profit_2022, 2) AS profit_2022, ROUND(profit_2023, 2) AS profit_2023,
       ROUND(growth_pct, 2)  AS growth_pct
FROM   growth
WHERE  rn <= 5
ORDER  BY rn;


-- Q19 | PRICING ACTION LIST: sub-categories where deep discounts (>5%) are common AND margin is weak
WITH sub AS (
    SELECT category, sub_category,
           SUM(net_revenue)                                         AS revenue,
           SUM(total_profit)                                        AS profit,
           SUM(CASE WHEN discount_percent > 5 THEN 1 ELSE 0 END)    AS deep_discount_lines,
           COUNT(*)                                                 AS lines
    FROM   df_orders
    GROUP  BY category, sub_category
)
SELECT category, sub_category,
       ROUND(100.0 * deep_discount_lines / lines, 2)  AS deep_discount_share_pct,
       ROUND(100.0 * profit / revenue, 2)             AS margin_pct,
       ROUND(revenue, 2)                              AS revenue
FROM   sub
ORDER  BY deep_discount_share_pct DESC;
