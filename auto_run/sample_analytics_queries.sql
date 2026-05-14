-- =============================================================================
-- TRADESTAT REGIONAL ANALYTICS QUERIES
-- 
-- Once data is loaded, run these queries to answer geopolitical questions
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────
-- Q1: India's exports by region (latest year)
-- ─────────────────────────────────────────────────────────────────────
SELECT 
    region,
    ROUND(SUM(value_usd)::numeric/1e9, 2) as exports_bn_usd
FROM dw.fact_trade_monthly 
WHERE source_system = 'TRADESTAT' 
  AND direction = 'EXPORT'
  AND date_key = 20240101
GROUP BY region 
ORDER BY exports_bn_usd DESC 
LIMIT 20;


-- ─────────────────────────────────────────────────────────────────────
-- Q2: Trade balance by region (latest year)
-- "Where do we have surplus vs deficit?"
-- ─────────────────────────────────────────────────────────────────────
SELECT 
    region,
    ROUND(SUM(CASE WHEN direction='EXPORT' THEN value_usd ELSE 0 END)::numeric/1e9, 2) as exports_bn,
    ROUND(SUM(CASE WHEN direction='IMPORT' THEN value_usd ELSE 0 END)::numeric/1e9, 2) as imports_bn,
    ROUND((SUM(CASE WHEN direction='EXPORT' THEN value_usd ELSE 0 END) - 
           SUM(CASE WHEN direction='IMPORT' THEN value_usd ELSE 0 END))::numeric/1e9, 2) as balance_bn
FROM dw.fact_trade_monthly
WHERE source_system = 'TRADESTAT' 
  AND date_key = 20240101
  AND region != 'WORLD'
GROUP BY region
ORDER BY balance_bn DESC;


-- ─────────────────────────────────────────────────────────────────────
-- Q3: Top trading regions over time (8-year trend)
-- ─────────────────────────────────────────────────────────────────────
SELECT 
    region,
    SUBSTRING(date_key::text, 1, 4) as year,
    ROUND(SUM(value_usd)::numeric/1e9, 2) as bn_usd
FROM dw.fact_trade_monthly
WHERE source_system = 'TRADESTAT'
  AND direction = 'EXPORT'
  AND region IN ('EUROPE', 'EU_COUNTRIES', 'NORTH_AMERICA', 'ASEAN', 'OPEC')
GROUP BY region, year
ORDER BY year, bn_usd DESC;


-- ─────────────────────────────────────────────────────────────────────
-- Q4: India's trade dependency on top regions (% share)
-- ─────────────────────────────────────────────────────────────────────
WITH world_totals AS (
    SELECT 
        direction,
        SUM(value_usd) as world_total
    FROM dw.fact_trade_monthly
    WHERE source_system = 'TRADESTAT' 
      AND region = 'WORLD'
      AND date_key = 20240101
    GROUP BY direction
)
SELECT 
    f.region,
    f.direction,
    ROUND(SUM(f.value_usd)::numeric/1e9, 2) as bn_usd,
    ROUND(100.0 * SUM(f.value_usd) / w.world_total, 2) as pct_of_world
FROM dw.fact_trade_monthly f
JOIN world_totals w ON w.direction = f.direction
WHERE f.source_system = 'TRADESTAT' 
  AND f.region != 'WORLD'
  AND f.date_key = 20240101
GROUP BY f.region, f.direction, w.world_total
HAVING SUM(f.value_usd) > 1e9
ORDER BY f.direction, pct_of_world DESC
LIMIT 30;


-- ─────────────────────────────────────────────────────────────────────
-- Q5: Top commodities by region (Europe vs America)
-- ─────────────────────────────────────────────────────────────────────
SELECT 
    f.region,
    h.hs_code,
    LEFT(h.description, 50) as commodity,
    ROUND(SUM(f.value_usd)::numeric/1e9, 2) as exports_bn_usd
FROM dw.fact_trade_monthly f
JOIN dw.dim_hs_code h ON h.hs_code_key = f.hs_code_key
WHERE f.source_system = 'TRADESTAT'
  AND f.direction = 'EXPORT'
  AND f.date_key = 20240101
  AND f.region IN ('EUROPE', 'NORTH_AMERICA')
GROUP BY f.region, h.hs_code, h.description
ORDER BY f.region, exports_bn_usd DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────────────────
-- Q6: Year-over-year growth by region
-- ─────────────────────────────────────────────────────────────────────
WITH yearly AS (
    SELECT 
        region,
        SUBSTRING(date_key::text, 1, 4)::int as year,
        SUM(value_usd) as total
    FROM dw.fact_trade_monthly
    WHERE source_system = 'TRADESTAT'
      AND direction = 'EXPORT'
    GROUP BY region, year
)
SELECT 
    region,
    year,
    ROUND(total::numeric/1e9, 2) as bn_usd,
    ROUND((100.0 * (total - LAG(total) OVER (PARTITION BY region ORDER BY year)) 
           / NULLIF(LAG(total) OVER (PARTITION BY region ORDER BY year), 0))::numeric, 2) 
           as yoy_growth_pct
FROM yearly
WHERE region IN ('EUROPE', 'EU_COUNTRIES', 'NORTH_AMERICA', 'ASEAN', 'CHINA', 'OPEC')
ORDER BY region, year;


-- ─────────────────────────────────────────────────────────────────────
-- Q7: Strategic concentration risk
-- "What % of exports go to top 5 regions?"
-- ─────────────────────────────────────────────────────────────────────
WITH region_totals AS (
    SELECT 
        region,
        SUM(value_usd) as total,
        ROW_NUMBER() OVER (ORDER BY SUM(value_usd) DESC) as rank
    FROM dw.fact_trade_monthly
    WHERE source_system = 'TRADESTAT'
      AND direction = 'EXPORT'
      AND region != 'WORLD'
      AND date_key = 20240101
    GROUP BY region
)
SELECT 
    'Top 5 regions' as metric,
    ROUND(100.0 * SUM(CASE WHEN rank <= 5 THEN total ELSE 0 END) / SUM(total), 2) as concentration_pct
FROM region_totals
UNION ALL
SELECT 
    'Top 10 regions',
    ROUND(100.0 * SUM(CASE WHEN rank <= 10 THEN total ELSE 0 END) / SUM(total), 2)
FROM region_totals;
