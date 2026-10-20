/* =====================================================================================
   01_create_table_sqlserver.sql
   Optional: create df_orders with explicit data types BEFORE loading from Python.
   (pandas.to_sql would otherwise create wide default types such as VARCHAR(max) / FLOAT.)

   Load flow:  1) run this script
               2) in ingest_and_clean.py change  if_exists="replace"  ->  if_exists="append"
               3) run the script with --db "mssql+pyodbc://..."
   ===================================================================================== */
CREATE DATABASE GlobalMart;
GO
USE GlobalMart;
GO

IF OBJECT_ID('dbo.df_orders', 'U') IS NOT NULL DROP TABLE dbo.df_orders;
GO

CREATE TABLE dbo.df_orders (
    order_id           INT            NOT NULL PRIMARY KEY,
    order_date         DATE           NOT NULL,
    ship_mode          VARCHAR(20)    NOT NULL,
    segment            VARCHAR(20)    NOT NULL,
    country            VARCHAR(30)    NOT NULL,
    city               VARCHAR(40)    NOT NULL,
    state              VARCHAR(40)    NOT NULL,
    postal_code        VARCHAR(10)    NULL,
    region             VARCHAR(10)    NOT NULL,
    category           VARCHAR(20)    NOT NULL,
    sub_category       VARCHAR(20)    NOT NULL,
    product_id         VARCHAR(20)    NOT NULL,
    cost_price         DECIMAL(12,2)  NOT NULL,
    list_price         DECIMAL(12,2)  NOT NULL,
    quantity           INT            NOT NULL,
    discount_percent   INT            NOT NULL,
    discount           DECIMAL(12,2)  NOT NULL,   -- per unit
    sale_price         DECIMAL(12,2)  NOT NULL,   -- per unit, post-discount
    profit             DECIMAL(12,2)  NOT NULL,   -- per unit
    gross_revenue      DECIMAL(14,2)  NOT NULL,   -- list_price x quantity (pre-discount)
    discount_amount    DECIMAL(14,2)  NOT NULL,
    net_revenue        DECIMAL(14,2)  NOT NULL,   -- sale_price x quantity (post-discount)
    total_cost         DECIMAL(14,2)  NOT NULL,
    total_profit       DECIMAL(14,2)  NOT NULL,
    profit_margin_pct  DECIMAL(8,2)   NULL,
    order_year         SMALLINT       NOT NULL,
    order_month        TINYINT        NOT NULL,
    order_month_name   CHAR(3)        NOT NULL,
    order_year_month   CHAR(7)        NOT NULL,
    order_quarter      CHAR(2)        NOT NULL,
    is_loss_making     BIT            NOT NULL,
    discount_band      VARCHAR(10)    NOT NULL
);
GO

CREATE INDEX ix_orders_date   ON dbo.df_orders (order_date);
CREATE INDEX ix_orders_region ON dbo.df_orders (region, city);
CREATE INDEX ix_orders_prod   ON dbo.df_orders (product_id);
GO
