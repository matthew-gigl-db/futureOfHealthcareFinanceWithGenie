# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# DBTITLE 1,Healthcare Finance Webinar — Data Foundation
# MAGIC %md
# MAGIC # Healthcare Finance Webinar — Data Foundation
# MAGIC
# MAGIC Seeds all 8 tables, 6 metric views, and validation queries into `hls_fde.healthcare_finance`.
# MAGIC
# MAGIC **Schema:** Parameterized via `catalog` and `schema` widgets (defaults: `hls_fde.healthcare_finance`)  
# MAGIC **Tables:** dim_aco_contract, dim_budget, dim_member, dim_provider_network, gold_financial_monthly, gold_quality_measures, gold_utilization_monthly, fact_vbc_performance  
# MAGIC **Metric Views:** mv_financial, mv_quality, mv_vbc_performance, mv_utilization, mv_budget_variance, mv_member_risk (all with daily materialization)  
# MAGIC **Data:** Synthetic, deterministic, with planted narrative for 4 demo beats

# COMMAND ----------

# DBTITLE 1,Create Widgets — catalog and schema
dbutils.widgets.text("catalog", "hls_fde", "Catalog")
dbutils.widgets.text("schema", "healthcare_finance", "Schema")

print(f"Using: {dbutils.widgets.get('catalog')}.{dbutils.widgets.get('schema')}")

# COMMAND ----------

# DBTITLE 1,Set default catalog and schema
# MAGIC %sql
# MAGIC USE CATALOG IDENTIFIER('${catalog}');
# MAGIC USE SCHEMA IDENTIFIER('${schema}');

# COMMAND ----------

# DBTITLE 1,DDL — dim_aco_contract
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `dim_aco_contract` (
# MAGIC   `aco_id` STRING NOT NULL COMMENT 'Unique ACO identifier',
# MAGIC   `aco_name` STRING NOT NULL COMMENT 'Full name of the Accountable Care Organization or clinically integrated network',
# MAGIC   `aco_short_name` STRING COMMENT 'Abbreviated name for display',
# MAGIC   `parent_system` STRING COMMENT 'Parent health system or organization',
# MAGIC   `exec_medical_director` STRING COMMENT 'Name of the Executive Medical Director or equivalent clinical leader',
# MAGIC   `exec_title` STRING COMMENT 'Title of the clinical executive (e.g., Executive Medical Director, CMO)',
# MAGIC   `contract_type` STRING COMMENT 'Type of value-based arrangement: Shared Savings, Capitation, Bundled Payment, CIN',
# MAGIC   `payers` STRING COMMENT 'Comma-separated list of payer partners',
# MAGIC   `region` STRING COMMENT 'Geographic region served',
# MAGIC   `counties_served` INT COMMENT 'Number of counties in the network footprint',
# MAGIC   `attributed_members` INT COMMENT 'Total members attributed to this ACO across all payer contracts',
# MAGIC   `provider_count` INT COMMENT 'Number of providers in the network',
# MAGIC   `hospital_count` INT COMMENT 'Number of hospitals in the network',
# MAGIC   `gainsharing_split_pcp_pct` DECIMAL(5,2) COMMENT 'Percentage of gainsharing pool allocated to PCPs',
# MAGIC   `gainsharing_split_specialist_pct` DECIMAL(5,2) COMMENT 'Percentage allocated to specialists',
# MAGIC   `gainsharing_split_hospital_pct` DECIMAL(5,2) COMMENT 'Percentage allocated to hospitals',
# MAGIC   `contract_start_date` DATE COMMENT 'Date the current VBC contract period began',
# MAGIC   `key_hospitals` STRING COMMENT 'Comma-separated list of major hospitals in the network',
# MAGIC   CONSTRAINT pk_dim_aco_contract PRIMARY KEY (`aco_id`)
# MAGIC )
# MAGIC COMMENT 'ACO and clinically integrated network reference data. Synthetic demo data. 5 fictional ACOs including one modeled on real AHP (Accountable Health Partners) structure.';

# COMMAND ----------

# DBTITLE 1,DDL — dim_budget
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `dim_budget` (
# MAGIC   `lob` STRING NOT NULL COMMENT 'Line of business: Commercial, MA, Medicaid, Individual',
# MAGIC   `year_month` DATE NOT NULL COMMENT 'First day of the month (e.g., 2026-01-01)',
# MAGIC   `target_mlr` DECIMAL(6,4) COMMENT 'Target Medical Loss Ratio for this LOB/month. Values like 0.8500 = 85%.',
# MAGIC   `target_paid_pmpm` DECIMAL(10,2) COMMENT 'Target paid claims PMPM for this LOB/month',
# MAGIC   `target_premium_pmpm` DECIMAL(10,2) COMMENT 'Target premium PMPM for this LOB/month',
# MAGIC   `budget_premium` DECIMAL(14,2) COMMENT 'Total budgeted premium revenue for this LOB/month',
# MAGIC   `budget_paid_claims` DECIMAL(14,2) COMMENT 'Total budgeted paid claims for this LOB/month',
# MAGIC   CONSTRAINT pk_dim_budget PRIMARY KEY (`lob`, `year_month`)
# MAGIC )
# MAGIC COMMENT 'Monthly budget targets by line of business. Used to calculate variance vs actuals. Synthetic demo data.';

# COMMAND ----------

# DBTITLE 1,DDL — dim_member
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `dim_member` (
# MAGIC   `member_id` STRING NOT NULL COMMENT 'Unique member identifier (synthetic)',
# MAGIC   `lob` STRING NOT NULL COMMENT 'Line of business',
# MAGIC   `state` STRING NOT NULL COMMENT 'Member state of residence',
# MAGIC   `age_band` STRING COMMENT 'Age band: 0-17, 18-34, 35-49, 50-64, 65+',
# MAGIC   `gender` STRING COMMENT 'Member gender: M, F',
# MAGIC   `plan_type` STRING COMMENT 'Plan type: PPO, HMO, EPO, POS',
# MAGIC   `risk_score` DECIMAL(6,4) COMMENT 'HCC risk adjustment factor. 1.0 = average. Higher = sicker/costlier.',
# MAGIC   `cost_percentile` INT COMMENT 'Cost percentile within LOB (1-100). 99 = top 1% costliest.',
# MAGIC   `open_gaps_count` INT COMMENT 'Number of open HEDIS care gaps for this member',
# MAGIC   `nba_recommendation` STRING COMMENT 'Next Best Action recommendation from care management model',
# MAGIC   `attributed_aco_id` STRING COMMENT 'ACO ID if member is attributed to a VBC contract (nullable)',
# MAGIC   CONSTRAINT pk_dim_member PRIMARY KEY (`member_id`),
# MAGIC   CONSTRAINT fk_dim_member_aco FOREIGN KEY (`attributed_aco_id`) REFERENCES `dim_aco_contract`(`aco_id`)
# MAGIC )
# MAGIC CLUSTER BY (`lob`, `state`)
# MAGIC COMMENT 'Member-level demographics and risk profile. Synthetic demo data. Do NOT expose member_id in user-facing queries — use for aggregation only.';

# COMMAND ----------

# DBTITLE 1,DDL — dim_provider_network
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `dim_provider_network` (
# MAGIC   `provider_id` STRING NOT NULL COMMENT 'Unique provider identifier (synthetic)',
# MAGIC   `provider_name` STRING NOT NULL COMMENT 'Provider display name (synthetic)',
# MAGIC   `specialty` STRING COMMENT 'Medical specialty: Primary Care, Cardiology, Endocrinology, Orthopedics, etc.',
# MAGIC   `aco_id` STRING NOT NULL COMMENT 'Foreign key to dim_aco_contract',
# MAGIC   `hospital_affiliation` STRING COMMENT 'Primary hospital affiliation',
# MAGIC   `attributed_members` INT COMMENT 'Number of members attributed to this provider',
# MAGIC   `cost_efficiency_score` DECIMAL(4,2) COMMENT 'Cost efficiency score (0-5 scale). 5 = most efficient.',
# MAGIC   `quality_composite_score` DECIMAL(4,2) COMMENT 'Quality composite score (0-5 scale). 5 = highest quality.',
# MAGIC   CONSTRAINT pk_dim_provider_network PRIMARY KEY (`provider_id`),
# MAGIC   CONSTRAINT fk_dim_provider_network_aco FOREIGN KEY (`aco_id`) REFERENCES `dim_aco_contract`(`aco_id`)
# MAGIC )
# MAGIC COMMENT 'Provider-level network data by ACO. Synthetic demo data.';

# COMMAND ----------

# DBTITLE 1,DDL — gold_financial_monthly
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `gold_financial_monthly` (
# MAGIC   `lob` STRING NOT NULL COMMENT 'Line of business: Commercial, MA, Medicaid, Individual',
# MAGIC   `state` STRING NOT NULL COMMENT 'US state abbreviation (e.g., NY, FL, TX, CA)',
# MAGIC   `plan_type` STRING NOT NULL COMMENT 'Plan type: PPO, HMO, EPO, POS',
# MAGIC   `year_month` DATE NOT NULL COMMENT 'First day of the month',
# MAGIC   `paid_amount` DECIMAL(14,2) COMMENT 'Total paid medical claims for this segment/month',
# MAGIC   `premium_amount` DECIMAL(14,2) COMMENT 'Total earned premium revenue for this segment/month',
# MAGIC   `member_months` BIGINT COMMENT 'Total member-months for this segment/month',
# MAGIC   `avoidable_paid_amount` DECIMAL(14,2) COMMENT 'Paid claims attributable to avoidable utilization (preventable ED, avoidable IP)',
# MAGIC   `risk_score_avg` DECIMAL(6,4) COMMENT 'Average HCC risk score for members in this segment/month'
# MAGIC )
# MAGIC CLUSTER BY (`lob`, `year_month`)
# MAGIC COMMENT 'Monthly financial performance aggregates by LOB, state, and plan type. Synthetic demo data. Query mv_financial metric view for governed KPIs.';

# COMMAND ----------

# DBTITLE 1,DDL — gold_quality_measures
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `gold_quality_measures` (
# MAGIC   `measure_id` STRING NOT NULL COMMENT 'HEDIS measure identifier (e.g., BCS, CDC-HBA1C, CBP)',
# MAGIC   `measure_name` STRING NOT NULL COMMENT 'Human-readable measure name',
# MAGIC   `lob` STRING NOT NULL COMMENT 'Line of business',
# MAGIC   `year_month` DATE NOT NULL COMMENT 'Measurement month',
# MAGIC   `current_rate` DECIMAL(6,4) COMMENT 'Current performance rate (0.0 to 1.0). E.g., 0.72 = 72% of eligible members completed.',
# MAGIC   `star_3_cutpoint` DECIMAL(6,4) COMMENT 'Rate threshold for 3-star rating',
# MAGIC   `star_4_cutpoint` DECIMAL(6,4) COMMENT 'Rate threshold for 4-star rating',
# MAGIC   `star_5_cutpoint` DECIMAL(6,4) COMMENT 'Rate threshold for 5-star rating',
# MAGIC   `eligible_count` INT COMMENT 'Number of members eligible for this measure',
# MAGIC   `gap_count` INT COMMENT 'Number of members with an open care gap (eligible but not completed)',
# MAGIC   `condition_domain` STRING COMMENT 'Clinical domain: Diabetes, Cardiovascular, Cancer Screening, Behavioral Health, Pediatric/Preventive'
# MAGIC )
# MAGIC CLUSTER BY (`lob`, `year_month`)
# MAGIC COMMENT 'HEDIS quality measure performance by LOB and month. Synthetic demo data. Query mv_quality metric view for governed KPIs.';

# COMMAND ----------

# DBTITLE 1,DDL — gold_utilization_monthly
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `gold_utilization_monthly` (
# MAGIC   `lob` STRING NOT NULL COMMENT 'Line of business',
# MAGIC   `state` STRING NOT NULL COMMENT 'US state abbreviation',
# MAGIC   `year_month` DATE NOT NULL COMMENT 'First day of the month',
# MAGIC   `ip_admits` INT COMMENT 'Inpatient admissions',
# MAGIC   `ed_visits` INT COMMENT 'Emergency department visits',
# MAGIC   `readmissions` INT COMMENT '30-day all-cause readmissions',
# MAGIC   `avoidable_ed_visits` INT COMMENT 'ED visits classified as avoidable (could have been treated in lower-cost setting)',
# MAGIC   `avoidable_ip_admits` INT COMMENT 'Inpatient admissions classified as potentially preventable',
# MAGIC   `op_visits` INT COMMENT 'Outpatient visits',
# MAGIC   `rx_fills` INT COMMENT 'Prescription fills',
# MAGIC   `member_months` BIGINT COMMENT 'Total member-months for this segment/month. Matches gold_financial_monthly for per-1K rate calculations.'
# MAGIC )
# MAGIC CLUSTER BY (`lob`, `year_month`)
# MAGIC COMMENT 'Monthly utilization aggregates by LOB and state. Synthetic demo data.';

# COMMAND ----------

# DBTITLE 1,DDL — fact_vbc_performance
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE `fact_vbc_performance` (
# MAGIC   `aco_id` STRING NOT NULL COMMENT 'Foreign key to dim_aco_contract',
# MAGIC   `measure_name` STRING NOT NULL COMMENT 'VBC performance measure: Shared Savings YTD, TCOC PMPM, Quality Score, Readmission Rate, ED Rate per 1K, Pharmacy PMPM',
# MAGIC   `quarter` STRING NOT NULL COMMENT 'Calendar quarter (e.g., 2026-Q1)',
# MAGIC   `actual_value` DECIMAL(14,4) COMMENT 'Actual performance value for this measure/quarter',
# MAGIC   `target_value` DECIMAL(14,4) COMMENT 'Contractual target or benchmark value',
# MAGIC   `benchmark_value` DECIMAL(14,4) COMMENT 'Regional or national benchmark for comparison',
# MAGIC   `trend_vs_prior_quarter` DECIMAL(8,4) COMMENT 'Percentage change vs prior quarter (e.g., 0.03 = +3%)',
# MAGIC   CONSTRAINT fk_fact_vbc_aco FOREIGN KEY (`aco_id`) REFERENCES `dim_aco_contract`(`aco_id`)
# MAGIC )
# MAGIC CLUSTER BY (`aco_id`, `quarter`)
# MAGIC COMMENT 'Quarterly value-based care performance by ACO and measure. Synthetic demo data. Query mv_vbc_performance metric view for governed KPIs.';

# COMMAND ----------

# DBTITLE 1,Seed — dim_aco_contract (5 rows)
# MAGIC %sql
# MAGIC INSERT INTO `dim_aco_contract` VALUES
# MAGIC -- AHP: modeled on real Accountable Health Partners structure
# MAGIC ('ACO-001', 'Accountable Health Partners (AHP)', 'AHP', 'UR Medicine / University of Rochester Medical Center',
# MAGIC  'Dr. Sarah Chen', 'Executive Medical Director', 'Multi-payer CIN (Shared Savings)',
# MAGIC  'Excellus BCBS, MVP Health Care', 'Finger Lakes, Upstate NY', 21, 150000, 4200, 13,
# MAGIC  60.00, 25.00, 15.00, '2024-01-01',
# MAGIC  'Strong Memorial, Highland, F.F. Thompson, Noyes Memorial, Jones Memorial'),
# MAGIC
# MAGIC ('ACO-002', 'Lakeshore Health Alliance', 'LHA', 'Great Lakes Health System',
# MAGIC  'Dr. Michael Torres', 'Chief Medical Officer', 'MSSP Track 2 (Shared Savings)',
# MAGIC  'Anthem BCBS', 'Great Lakes, OH', 8, 85000, 1800, 5,
# MAGIC  55.00, 30.00, 15.00, '2024-01-01',
# MAGIC  'Lakeside Medical Center, Harbor General'),
# MAGIC
# MAGIC ('ACO-003', 'Piedmont Integrated Care', 'PIC', 'Piedmont Health Network',
# MAGIC  'Dr. Angela Washington', 'Executive Medical Director', 'Shared Savings + Quality Bonus',
# MAGIC  'BCBS of NC, Aetna', 'Piedmont, NC', 12, 110000, 2500, 7,
# MAGIC  60.00, 25.00, 15.00, '2023-07-01',
# MAGIC  'Piedmont Regional, Mountain View Hospital'),
# MAGIC
# MAGIC ('ACO-004', 'Valley Care Partners', 'VCP', 'Central Valley Medical Group',
# MAGIC  'Dr. James Park', 'Chief Medical Officer', 'Capitation + Shared Savings',
# MAGIC  'Blue Shield of CA, Health Net', 'Central Valley, CA', 6, 72000, 1200, 4,
# MAGIC  50.00, 30.00, 20.00, '2024-01-01',
# MAGIC  'Valley Medical Center, Sunrise Community Hospital'),
# MAGIC
# MAGIC ('ACO-005', 'Gulf Coast Health Collaborative', 'GCHC', 'Gulf Coast Medical Partners',
# MAGIC  'Dr. Maria Gonzalez', 'VP Clinical Integration', 'MSSP Track 1+ (Shared Savings)',
# MAGIC  'Florida Blue, Humana', 'Gulf Coast, FL', 10, 95000, 2100, 6,
# MAGIC  55.00, 25.00, 20.00, '2024-01-01',
# MAGIC  'Gulf Coast Regional, Bayshore Medical Center');

# COMMAND ----------

# DBTITLE 1,Seed — dim_budget (60 rows)
# MAGIC %sql
# MAGIC INSERT INTO `dim_budget`
# MAGIC SELECT
# MAGIC   lob,
# MAGIC   year_month,
# MAGIC   CASE lob
# MAGIC     WHEN 'Commercial' THEN 0.8500
# MAGIC     WHEN 'Individual' THEN 0.8200
# MAGIC     WHEN 'MA' THEN 0.9800
# MAGIC     WHEN 'Medicaid' THEN 1.0000
# MAGIC   END AS target_mlr,
# MAGIC   CASE lob
# MAGIC     WHEN 'Commercial' THEN 520.00
# MAGIC     WHEN 'Individual' THEN 560.00
# MAGIC     WHEN 'MA' THEN 1070.00
# MAGIC     WHEN 'Medicaid' THEN 880.00
# MAGIC   END AS target_paid_pmpm,
# MAGIC   CASE lob
# MAGIC     WHEN 'Commercial' THEN 612.00
# MAGIC     WHEN 'Individual' THEN 683.00
# MAGIC     WHEN 'MA' THEN 1092.00
# MAGIC     WHEN 'Medicaid' THEN 880.00
# MAGIC   END AS target_premium_pmpm,
# MAGIC   CASE lob
# MAGIC     WHEN 'Commercial' THEN 12200000.00
# MAGIC     WHEN 'Individual' THEN 3410000.00
# MAGIC     WHEN 'MA' THEN 13700000.00
# MAGIC     WHEN 'Medicaid' THEN 11060000.00
# MAGIC   END AS budget_premium,
# MAGIC   CASE lob
# MAGIC     WHEN 'Commercial' THEN 10370000.00
# MAGIC     WHEN 'Individual' THEN 2796000.00
# MAGIC     WHEN 'MA' THEN 13426000.00
# MAGIC     WHEN 'Medicaid' THEN 11060000.00
# MAGIC   END AS budget_paid_claims
# MAGIC FROM (
# MAGIC   SELECT EXPLODE(ARRAY('Commercial', 'Individual', 'MA', 'Medicaid')) AS lob
# MAGIC ) lobs
# MAGIC CROSS JOIN (
# MAGIC   SELECT EXPLODE(SEQUENCE(DATE'2025-06-01', DATE'2026-08-01', INTERVAL 1 MONTH)) AS year_month
# MAGIC ) months;

# COMMAND ----------

# DBTITLE 1,Seed — gold_financial_monthly (600 rows)
# MAGIC %sql
# MAGIC INSERT INTO `gold_financial_monthly`
# MAGIC WITH months AS (
# MAGIC   SELECT EXPLODE(SEQUENCE(DATE'2025-06-01', DATE'2026-08-01', INTERVAL 1 MONTH)) AS year_month
# MAGIC ),
# MAGIC states AS (
# MAGIC   SELECT EXPLODE(ARRAY('NY','FL','TX','CA','PA','OH','IL','GA','NC','MI')) AS state
# MAGIC ),
# MAGIC lobs AS (
# MAGIC   SELECT EXPLODE(ARRAY('Commercial','MA','Medicaid','Individual')) AS lob
# MAGIC ),
# MAGIC base AS (
# MAGIC   SELECT l.lob, s.state, m.year_month,
# MAGIC     MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') AS month_idx
# MAGIC   FROM lobs l CROSS JOIN states s CROSS JOIN months m
# MAGIC )
# MAGIC SELECT
# MAGIC   lob,
# MAGIC   state,
# MAGIC   'PPO' AS plan_type,
# MAGIC   year_month,
# MAGIC
# MAGIC   ROUND(
# MAGIC     CASE lob
# MAGIC       WHEN 'Commercial' THEN (520 + month_idx * 1.5 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 20)
# MAGIC       WHEN 'Individual' THEN (560 + month_idx * 1.2 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 18)
# MAGIC       WHEN 'MA'         THEN (1080 + month_idx * 2.0 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 30)
# MAGIC       WHEN 'Medicaid'   THEN (910 + month_idx * 2.5 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 25)
# MAGIC     END
# MAGIC     * CASE lob
# MAGIC       WHEN 'Commercial' THEN (1800 + ABS(HASH(CONCAT(state, 'cm'))) % 400)
# MAGIC       WHEN 'Individual' THEN (400 + ABS(HASH(CONCAT(state, 'ind'))) % 150)
# MAGIC       WHEN 'MA'         THEN (1100 + ABS(HASH(CONCAT(state, 'ma'))) % 300)
# MAGIC       WHEN 'Medicaid'   THEN (1100 + ABS(HASH(CONCAT(state, 'med'))) % 300)
# MAGIC     END
# MAGIC   , 2) AS paid_amount,
# MAGIC
# MAGIC   ROUND(
# MAGIC     CASE lob
# MAGIC       WHEN 'Commercial' THEN (600 + month_idx * 1.8 + HASH(CONCAT(state, lob, 'p', CAST(year_month AS STRING))) % 15)
# MAGIC       WHEN 'Individual' THEN (680 + month_idx * 1.5 + HASH(CONCAT(state, lob, 'p', CAST(year_month AS STRING))) % 12)
# MAGIC       WHEN 'MA'         THEN (1078 + month_idx * 1.5 + HASH(CONCAT(state, lob, 'p', CAST(year_month AS STRING))) % 20)
# MAGIC       WHEN 'Medicaid'   THEN (862 + month_idx * 1.0 + HASH(CONCAT(state, lob, 'p', CAST(year_month AS STRING))) % 15)
# MAGIC     END
# MAGIC     * CASE lob
# MAGIC       WHEN 'Commercial' THEN (1800 + ABS(HASH(CONCAT(state, 'cm'))) % 400)
# MAGIC       WHEN 'Individual' THEN (400 + ABS(HASH(CONCAT(state, 'ind'))) % 150)
# MAGIC       WHEN 'MA'         THEN (1100 + ABS(HASH(CONCAT(state, 'ma'))) % 300)
# MAGIC       WHEN 'Medicaid'   THEN (1100 + ABS(HASH(CONCAT(state, 'med'))) % 300)
# MAGIC     END
# MAGIC   , 2) AS premium_amount,
# MAGIC
# MAGIC   CAST(CASE lob
# MAGIC     WHEN 'Commercial' THEN (1800 + ABS(HASH(CONCAT(state, 'cm'))) % 400)
# MAGIC     WHEN 'Individual' THEN (400 + ABS(HASH(CONCAT(state, 'ind'))) % 150)
# MAGIC     WHEN 'MA'         THEN (1100 + ABS(HASH(CONCAT(state, 'ma'))) % 300)
# MAGIC     WHEN 'Medicaid'   THEN (1100 + ABS(HASH(CONCAT(state, 'med'))) % 300)
# MAGIC   END AS BIGINT) AS member_months,
# MAGIC
# MAGIC   ROUND(
# MAGIC     CASE lob
# MAGIC       WHEN 'Commercial' THEN (520 + month_idx * 1.5 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 20)
# MAGIC       WHEN 'Individual' THEN (560 + month_idx * 1.2 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 18)
# MAGIC       WHEN 'MA'         THEN (1080 + month_idx * 2.0 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 30)
# MAGIC       WHEN 'Medicaid'   THEN (910 + month_idx * 2.5 + HASH(CONCAT(state, lob, CAST(year_month AS STRING))) % 25)
# MAGIC     END
# MAGIC     * CASE lob
# MAGIC       WHEN 'Commercial' THEN (1800 + ABS(HASH(CONCAT(state, 'cm'))) % 400)
# MAGIC       WHEN 'Individual' THEN (400 + ABS(HASH(CONCAT(state, 'ind'))) % 150)
# MAGIC       WHEN 'MA'         THEN (1100 + ABS(HASH(CONCAT(state, 'ma'))) % 300)
# MAGIC       WHEN 'Medicaid'   THEN (1100 + ABS(HASH(CONCAT(state, 'med'))) % 300)
# MAGIC     END
# MAGIC     * CASE WHEN state IN ('FL','TX','CA') THEN 0.14 ELSE 0.07 END
# MAGIC   , 2) AS avoidable_paid_amount,
# MAGIC
# MAGIC   ROUND(CASE lob
# MAGIC     WHEN 'Commercial' THEN 1.00 + month_idx * 0.002
# MAGIC     WHEN 'Individual' THEN 1.05 + month_idx * 0.003
# MAGIC     WHEN 'MA'         THEN 1.15 + month_idx * 0.005
# MAGIC     WHEN 'Medicaid'   THEN 1.08 + month_idx * 0.003
# MAGIC   END, 4) AS risk_score_avg
# MAGIC
# MAGIC FROM base;

# COMMAND ----------

# DBTITLE 1,Seed — dim_member (50,000 rows)
# MAGIC %sql
# MAGIC INSERT INTO `dim_member`
# MAGIC WITH member_ids AS (
# MAGIC   SELECT EXPLODE(SEQUENCE(1, 50000)) AS id
# MAGIC ),
# MAGIC base AS (
# MAGIC   SELECT
# MAGIC     id,
# MAGIC     CONCAT('MBR-', LPAD(CAST(id AS STRING), 6, '0')) AS member_id,
# MAGIC     CASE
# MAGIC       WHEN id <= 20000 THEN 'Commercial'
# MAGIC       WHEN id <= 32500 THEN 'MA'
# MAGIC       WHEN id <= 45000 THEN 'Medicaid'
# MAGIC       ELSE 'Individual'
# MAGIC     END AS lob,
# MAGIC     ARRAY('NY','FL','TX','CA','PA','OH','IL','GA','NC','MI')[ABS(HASH(CONCAT('state', id))) % 10] AS state,
# MAGIC     CASE ABS(HASH(CONCAT('age', id))) % 10
# MAGIC       WHEN 0 THEN '0-17'  WHEN 1 THEN '0-17'
# MAGIC       WHEN 2 THEN '18-34' WHEN 3 THEN '18-34'
# MAGIC       WHEN 4 THEN '35-49' WHEN 5 THEN '35-49'
# MAGIC       WHEN 6 THEN '50-64' WHEN 7 THEN '50-64'
# MAGIC       WHEN 8 THEN '65+'   ELSE '65+'
# MAGIC     END AS age_band,
# MAGIC     CASE ABS(HASH(CONCAT('gender', id))) % 2 WHEN 0 THEN 'M' ELSE 'F' END AS gender,
# MAGIC     'PPO' AS plan_type
# MAGIC   FROM member_ids
# MAGIC )
# MAGIC SELECT
# MAGIC   member_id,
# MAGIC   lob,
# MAGIC   state,
# MAGIC   age_band,
# MAGIC   gender,
# MAGIC   plan_type,
# MAGIC
# MAGIC   ROUND(GREATEST(0.2,
# MAGIC     CASE lob
# MAGIC       WHEN 'Commercial' THEN 1.0
# MAGIC       WHEN 'MA'         THEN 1.2
# MAGIC       WHEN 'Medicaid'   THEN 1.1
# MAGIC       WHEN 'Individual' THEN 1.05
# MAGIC     END
# MAGIC     + (ABS(HASH(CONCAT('risk', member_id))) % 100 - 50) * 0.02
# MAGIC     + CASE WHEN age_band = '65+' THEN 0.3 WHEN age_band = '50-64' THEN 0.15 ELSE 0 END
# MAGIC     + CASE WHEN id <= 100 THEN 2.0 + (ABS(HASH(CONCAT('highrisk', member_id))) % 100) * 0.02 ELSE 0 END
# MAGIC   ), 4) AS risk_score,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN id <= 100 THEN 95 + ABS(HASH(CONCAT('pct', member_id))) % 5
# MAGIC     ELSE 1 + ABS(HASH(CONCAT('pct', member_id))) % 99
# MAGIC   END AS cost_percentile,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN id <= 100 THEN 8 + ABS(HASH(CONCAT('gaps', member_id))) % 5
# MAGIC     WHEN ABS(HASH(CONCAT('gaps2', member_id))) % 10 < 3 THEN 1 + ABS(HASH(CONCAT('gaps3', member_id))) % 4
# MAGIC     ELSE 0
# MAGIC   END AS open_gaps_count,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN id <= 100 THEN
# MAGIC       ARRAY('Schedule HbA1c test', 'Outreach for breast cancer screening', 'Care coordination referral',
# MAGIC             'Medication adherence follow-up', 'Diabetic eye exam reminder')[ABS(HASH(CONCAT('nba', member_id))) % 5]
# MAGIC     WHEN ABS(HASH(CONCAT('gaps2', member_id))) % 10 < 3 THEN
# MAGIC       ARRAY('Schedule preventive visit', 'Colorectal screening reminder', 'BP check follow-up',
# MAGIC             'Well-child visit reminder', 'Depression screening')[ABS(HASH(CONCAT('nba2', member_id))) % 5]
# MAGIC     ELSE NULL
# MAGIC   END AS nba_recommendation,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN lob = 'MA' AND ABS(HASH(CONCAT('aco', member_id))) % 10 < 3 THEN
# MAGIC       ARRAY('ACO-001','ACO-002','ACO-003','ACO-004','ACO-005')[ABS(HASH(CONCAT('aco2', member_id))) % 5]
# MAGIC     ELSE NULL
# MAGIC   END AS attributed_aco_id
# MAGIC
# MAGIC FROM base;

# COMMAND ----------

# DBTITLE 1,Seed — gold_quality_measures (360 rows)
# MAGIC %sql
# MAGIC INSERT INTO `gold_quality_measures`
# MAGIC WITH months AS (
# MAGIC   SELECT EXPLODE(SEQUENCE(DATE'2025-06-01', DATE'2026-08-01', INTERVAL 1 MONTH)) AS year_month
# MAGIC ),
# MAGIC lobs AS (
# MAGIC   SELECT EXPLODE(ARRAY('Commercial','MA','Medicaid','Individual')) AS lob
# MAGIC ),
# MAGIC measures AS (
# MAGIC   SELECT * FROM VALUES
# MAGIC     ('BCS',       'Breast Cancer Screening',                    'Cancer Screening',       0.6800, 0.7400, 0.8000),
# MAGIC     ('CCS',       'Colorectal Cancer Screening',                'Cancer Screening',       0.6500, 0.7200, 0.7800),
# MAGIC     ('CDC-HBA1C', 'Diabetes HbA1c Control (<8.0%)',             'Diabetes',               0.5200, 0.6000, 0.6800),
# MAGIC     ('CDC-EYE',   'Diabetic Eye Examination',                   'Diabetes',               0.5500, 0.6500, 0.7200),
# MAGIC     ('CBP',       'Controlling High Blood Pressure (<140/90)',  'Cardiovascular',         0.5800, 0.6800, 0.7500),
# MAGIC     ('FUH-7',     'Follow-Up After Hospitalization (7 days)',   'Behavioral Health',      0.4000, 0.5000, 0.6000)
# MAGIC   AS t(measure_id, measure_name, condition_domain, star_3_cutpoint, star_4_cutpoint, star_5_cutpoint)
# MAGIC )
# MAGIC SELECT
# MAGIC   ms.measure_id,
# MAGIC   ms.measure_name,
# MAGIC   l.lob,
# MAGIC   m.year_month,
# MAGIC
# MAGIC   ROUND(CASE
# MAGIC     WHEN ms.measure_id = 'BCS' AND l.lob = 'MA' THEN 0.70 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'BCS' THEN 0.74 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CDC-HBA1C' AND l.lob = 'MA' THEN 0.56 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CDC-HBA1C' THEN 0.60 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CBP' THEN 0.68 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CCS' AND l.lob = 'MA' THEN 0.71 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CCS' THEN 0.73 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'CDC-EYE' THEN 0.63 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     WHEN ms.measure_id = 'FUH-7' THEN 0.48 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC     ELSE 0.65
# MAGIC   END, 4) AS current_rate,
# MAGIC
# MAGIC   ms.star_3_cutpoint,
# MAGIC   ms.star_4_cutpoint,
# MAGIC   ms.star_5_cutpoint,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 8000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 2000
# MAGIC     WHEN 'MA'         THEN 5000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 1500
# MAGIC     WHEN 'Medicaid'   THEN 5000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 1500
# MAGIC     WHEN 'Individual' THEN 2000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 500
# MAGIC   END AS INT) AS eligible_count,
# MAGIC
# MAGIC   CAST(ROUND(
# MAGIC     CASE l.lob
# MAGIC       WHEN 'Commercial' THEN 8000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 2000
# MAGIC       WHEN 'MA'         THEN 5000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 1500
# MAGIC       WHEN 'Medicaid'   THEN 5000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 1500
# MAGIC       WHEN 'Individual' THEN 2000 + ABS(HASH(CONCAT(ms.measure_id, l.lob))) % 500
# MAGIC     END
# MAGIC     * (1.0 - CASE
# MAGIC       WHEN ms.measure_id = 'BCS' AND l.lob = 'MA' THEN 0.70 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'BCS' THEN 0.74 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CDC-HBA1C' AND l.lob = 'MA' THEN 0.56 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CDC-HBA1C' THEN 0.60 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CBP' THEN 0.68 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CCS' AND l.lob = 'MA' THEN 0.71 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CCS' THEN 0.73 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'CDC-EYE' THEN 0.63 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       WHEN ms.measure_id = 'FUH-7' THEN 0.48 + MONTHS_BETWEEN(m.year_month, DATE'2025-06-01') * 0.002
# MAGIC       ELSE 0.65
# MAGIC     END)
# MAGIC   ) AS INT) AS gap_count,
# MAGIC
# MAGIC   ms.condition_domain
# MAGIC
# MAGIC FROM measures ms CROSS JOIN lobs l CROSS JOIN months m;

# COMMAND ----------

# DBTITLE 1,Seed — gold_utilization_monthly (600 rows)
# MAGIC %sql
# MAGIC INSERT INTO `gold_utilization_monthly`
# MAGIC WITH months AS (
# MAGIC   SELECT EXPLODE(SEQUENCE(DATE'2025-06-01', DATE'2026-08-01', INTERVAL 1 MONTH)) AS year_month
# MAGIC ),
# MAGIC states AS (
# MAGIC   SELECT EXPLODE(ARRAY('NY','FL','TX','CA','PA','OH','IL','GA','NC','MI')) AS state
# MAGIC ),
# MAGIC lobs AS (
# MAGIC   SELECT EXPLODE(ARRAY('Commercial','MA','Medicaid','Individual')) AS lob
# MAGIC )
# MAGIC SELECT
# MAGIC   l.lob, s.state, m.year_month,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 45 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 15
# MAGIC     WHEN 'MA'         THEN 65 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 20
# MAGIC     WHEN 'Medicaid'   THEN 55 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 18
# MAGIC     WHEN 'Individual' THEN 20 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 10
# MAGIC   END AS INT) AS ip_admits,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 180 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 40
# MAGIC     WHEN 'MA'         THEN 220 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 50
# MAGIC     WHEN 'Medicaid'   THEN 250 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 60
# MAGIC     WHEN 'Individual' THEN 80 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 20
# MAGIC   END AS INT) AS ed_visits,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 5 + ABS(HASH(CONCAT(s.state, l.lob, 'ra', CAST(m.year_month AS STRING)))) % 4
# MAGIC     WHEN 'MA'         THEN 8 + ABS(HASH(CONCAT(s.state, l.lob, 'ra', CAST(m.year_month AS STRING)))) % 5
# MAGIC     WHEN 'Medicaid'   THEN 7 + ABS(HASH(CONCAT(s.state, l.lob, 'ra', CAST(m.year_month AS STRING)))) % 5
# MAGIC     WHEN 'Individual' THEN 2 + ABS(HASH(CONCAT(s.state, l.lob, 'ra', CAST(m.year_month AS STRING)))) % 3
# MAGIC   END AS INT) AS readmissions,
# MAGIC
# MAGIC   CAST(ROUND(
# MAGIC     CASE l.lob
# MAGIC       WHEN 'Commercial' THEN 180 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 40
# MAGIC       WHEN 'MA'         THEN 220 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 50
# MAGIC       WHEN 'Medicaid'   THEN 250 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 60
# MAGIC       WHEN 'Individual' THEN 80 + ABS(HASH(CONCAT(s.state, l.lob, 'ed', CAST(m.year_month AS STRING)))) % 20
# MAGIC     END
# MAGIC     * CASE WHEN s.state IN ('FL','TX','CA') THEN 0.35 ELSE 0.17 END
# MAGIC   ) AS INT) AS avoidable_ed_visits,
# MAGIC
# MAGIC   CAST(ROUND(
# MAGIC     CASE l.lob
# MAGIC       WHEN 'Commercial' THEN 45 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 15
# MAGIC       WHEN 'MA'         THEN 65 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 20
# MAGIC       WHEN 'Medicaid'   THEN 55 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 18
# MAGIC       WHEN 'Individual' THEN 20 + ABS(HASH(CONCAT(s.state, l.lob, CAST(m.year_month AS STRING)))) % 10
# MAGIC     END
# MAGIC     * CASE WHEN s.state IN ('FL','TX','CA') THEN 0.20 ELSE 0.10 END
# MAGIC   ) AS INT) AS avoidable_ip_admits,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 1200 + ABS(HASH(CONCAT(s.state, l.lob, 'op', CAST(m.year_month AS STRING)))) % 300
# MAGIC     WHEN 'MA'         THEN 900 + ABS(HASH(CONCAT(s.state, l.lob, 'op', CAST(m.year_month AS STRING)))) % 250
# MAGIC     WHEN 'Medicaid'   THEN 800 + ABS(HASH(CONCAT(s.state, l.lob, 'op', CAST(m.year_month AS STRING)))) % 200
# MAGIC     WHEN 'Individual' THEN 400 + ABS(HASH(CONCAT(s.state, l.lob, 'op', CAST(m.year_month AS STRING)))) % 100
# MAGIC   END AS INT) AS op_visits,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN 3500 + ABS(HASH(CONCAT(s.state, l.lob, 'rx', CAST(m.year_month AS STRING)))) % 500
# MAGIC     WHEN 'MA'         THEN 4200 + ABS(HASH(CONCAT(s.state, l.lob, 'rx', CAST(m.year_month AS STRING)))) % 600
# MAGIC     WHEN 'Medicaid'   THEN 3800 + ABS(HASH(CONCAT(s.state, l.lob, 'rx', CAST(m.year_month AS STRING)))) % 500
# MAGIC     WHEN 'Individual' THEN 1200 + ABS(HASH(CONCAT(s.state, l.lob, 'rx', CAST(m.year_month AS STRING)))) % 200
# MAGIC   END AS INT) AS rx_fills,
# MAGIC
# MAGIC   CAST(CASE l.lob
# MAGIC     WHEN 'Commercial' THEN (1800 + ABS(HASH(CONCAT(s.state, 'cm'))) % 400)
# MAGIC     WHEN 'Individual' THEN (400 + ABS(HASH(CONCAT(s.state, 'ind'))) % 150)
# MAGIC     WHEN 'MA'         THEN (1100 + ABS(HASH(CONCAT(s.state, 'ma'))) % 300)
# MAGIC     WHEN 'Medicaid'   THEN (1100 + ABS(HASH(CONCAT(s.state, 'med'))) % 300)
# MAGIC   END AS BIGINT) AS member_months
# MAGIC
# MAGIC FROM lobs l CROSS JOIN states s CROSS JOIN months m;

# COMMAND ----------

# DBTITLE 1,Seed — fact_vbc_performance (120 rows)
# MAGIC %sql
# MAGIC INSERT INTO `fact_vbc_performance`
# MAGIC WITH acos AS (
# MAGIC   SELECT EXPLODE(ARRAY('ACO-001','ACO-002','ACO-003','ACO-004','ACO-005')) AS aco_id
# MAGIC ),
# MAGIC quarters AS (
# MAGIC   SELECT EXPLODE(ARRAY('2025-Q4','2026-Q1','2026-Q2','2026-Q3')) AS quarter
# MAGIC ),
# MAGIC measures AS (
# MAGIC   SELECT EXPLODE(ARRAY(
# MAGIC     'Shared Savings YTD', 'TCOC PMPM', 'Quality Score',
# MAGIC     'Readmission Rate', 'ED Rate per 1K', 'Pharmacy PMPM'
# MAGIC   )) AS measure_name
# MAGIC )
# MAGIC SELECT
# MAGIC   a.aco_id,
# MAGIC   ms.measure_name,
# MAGIC   q.quarter,
# MAGIC
# MAGIC   ROUND(CASE
# MAGIC     WHEN ms.measure_name = 'Shared Savings YTD' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 1800000 WHEN '2026-Q1' THEN 520000 WHEN '2026-Q2' THEN 1250000 WHEN '2026-Q3' THEN 2100000 END
# MAGIC     WHEN ms.measure_name = 'Shared Savings YTD' THEN
# MAGIC       800000 + ABS(HASH(CONCAT(a.aco_id, q.quarter))) % 600000
# MAGIC
# MAGIC     WHEN ms.measure_name = 'TCOC PMPM' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 855 WHEN '2026-Q1' THEN 868 WHEN '2026-Q2' THEN 878 WHEN '2026-Q3' THEN 892 END
# MAGIC     WHEN ms.measure_name = 'TCOC PMPM' THEN
# MAGIC       820 + ABS(HASH(CONCAT(a.aco_id, q.quarter, 'tcoc'))) % 80
# MAGIC
# MAGIC     WHEN ms.measure_name = 'Quality Score' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 4.05 WHEN '2026-Q1' THEN 4.10 WHEN '2026-Q2' THEN 4.15 WHEN '2026-Q3' THEN 4.20 END
# MAGIC     WHEN ms.measure_name = 'Quality Score' THEN
# MAGIC       3.5 + (ABS(HASH(CONCAT(a.aco_id, q.quarter, 'qs'))) % 10) * 0.1
# MAGIC
# MAGIC     WHEN ms.measure_name = 'Readmission Rate' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 0.125 WHEN '2026-Q1' THEN 0.120 WHEN '2026-Q2' THEN 0.115 WHEN '2026-Q3' THEN 0.112 END
# MAGIC     WHEN ms.measure_name = 'Readmission Rate' THEN
# MAGIC       0.10 + (ABS(HASH(CONCAT(a.aco_id, q.quarter, 'rr'))) % 5) * 0.01
# MAGIC
# MAGIC     WHEN ms.measure_name = 'ED Rate per 1K' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 305 WHEN '2026-Q1' THEN 298 WHEN '2026-Q2' THEN 290 WHEN '2026-Q3' THEN 285 END
# MAGIC     WHEN ms.measure_name = 'ED Rate per 1K' THEN
# MAGIC       270 + ABS(HASH(CONCAT(a.aco_id, q.quarter, 'ed'))) % 40
# MAGIC
# MAGIC     WHEN ms.measure_name = 'Pharmacy PMPM' AND a.aco_id = 'ACO-001' THEN
# MAGIC       CASE q.quarter WHEN '2025-Q4' THEN 165 WHEN '2026-Q1' THEN 175 WHEN '2026-Q2' THEN 185 WHEN '2026-Q3' THEN 198 END
# MAGIC     WHEN ms.measure_name = 'Pharmacy PMPM' THEN
# MAGIC       150 + ABS(HASH(CONCAT(a.aco_id, q.quarter, 'rx'))) % 30
# MAGIC
# MAGIC     ELSE 0
# MAGIC   END, 4) AS actual_value,
# MAGIC
# MAGIC   ROUND(CASE
# MAGIC     WHEN ms.measure_name = 'Shared Savings YTD' AND a.aco_id = 'ACO-001' THEN 1800000
# MAGIC     WHEN ms.measure_name = 'Shared Savings YTD' THEN 700000 + ABS(HASH(CONCAT(a.aco_id, 'tgt'))) % 400000
# MAGIC     WHEN ms.measure_name = 'TCOC PMPM' THEN 865
# MAGIC     WHEN ms.measure_name = 'Quality Score' THEN 4.00
# MAGIC     WHEN ms.measure_name = 'Readmission Rate' THEN 0.120
# MAGIC     WHEN ms.measure_name = 'ED Rate per 1K' THEN 300
# MAGIC     WHEN ms.measure_name = 'Pharmacy PMPM' THEN 175
# MAGIC     ELSE 0
# MAGIC   END, 4) AS target_value,
# MAGIC
# MAGIC   ROUND(CASE
# MAGIC     WHEN ms.measure_name = 'Shared Savings YTD' THEN 1500000
# MAGIC     WHEN ms.measure_name = 'TCOC PMPM' THEN 880
# MAGIC     WHEN ms.measure_name = 'Quality Score' THEN 3.80
# MAGIC     WHEN ms.measure_name = 'Readmission Rate' THEN 0.130
# MAGIC     WHEN ms.measure_name = 'ED Rate per 1K' THEN 310
# MAGIC     WHEN ms.measure_name = 'Pharmacy PMPM' THEN 180
# MAGIC     ELSE 0
# MAGIC   END, 4) AS benchmark_value,
# MAGIC
# MAGIC   ROUND(CASE
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'TCOC PMPM' THEN 0.03
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'Pharmacy PMPM' THEN 0.08
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'Shared Savings YTD' THEN 0.15
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'Quality Score' THEN 0.02
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'Readmission Rate' THEN -0.01
# MAGIC     WHEN a.aco_id = 'ACO-001' AND ms.measure_name = 'ED Rate per 1K' THEN -0.02
# MAGIC     ELSE (ABS(HASH(CONCAT(a.aco_id, ms.measure_name, q.quarter))) % 10 - 5) * 0.01
# MAGIC   END, 4) AS trend_vs_prior_quarter
# MAGIC
# MAGIC FROM acos a CROSS JOIN quarters q CROSS JOIN measures ms;

# COMMAND ----------

# DBTITLE 1,Seed — dim_provider_network (200 rows)
# MAGIC %sql
# MAGIC INSERT INTO `dim_provider_network`
# MAGIC WITH provider_ids AS (
# MAGIC   SELECT EXPLODE(SEQUENCE(1, 200)) AS id
# MAGIC )
# MAGIC SELECT
# MAGIC   CONCAT('PRV-', LPAD(CAST(id AS STRING), 4, '0')) AS provider_id,
# MAGIC
# MAGIC   CONCAT(
# MAGIC     'Dr. ',
# MAGIC     ARRAY('James','Maria','Robert','Linda','David','Patricia','Michael','Jennifer','William','Elizabeth',
# MAGIC           'Richard','Susan','Thomas','Karen','Charles','Nancy','Daniel','Lisa','Matthew','Sarah',
# MAGIC           'Anthony','Betty','Mark','Dorothy','Steven','Sandra','Paul','Ashley','Andrew','Kimberly',
# MAGIC           'Joshua','Emily','Kenneth','Donna','Kevin','Michelle','Brian','Carol','George','Amanda')[ABS(HASH(CONCAT('first', id))) % 40],
# MAGIC     ' ',
# MAGIC     ARRAY('Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
# MAGIC           'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
# MAGIC           'Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson')[ABS(HASH(CONCAT('last', id))) % 30]
# MAGIC   ) AS provider_name,
# MAGIC
# MAGIC   ARRAY('Primary Care','Primary Care','Primary Care','Primary Care',
# MAGIC         'Cardiology','Endocrinology','Orthopedics',
# MAGIC         'Behavioral Health','Behavioral Health','Pulmonology')[ABS(HASH(CONCAT('spec', id))) % 10] AS specialty,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN id <= 80  THEN 'ACO-001'
# MAGIC     WHEN id <= 110 THEN 'ACO-002'
# MAGIC     WHEN id <= 140 THEN 'ACO-003'
# MAGIC     WHEN id <= 170 THEN 'ACO-004'
# MAGIC     ELSE 'ACO-005'
# MAGIC   END AS aco_id,
# MAGIC
# MAGIC   CASE
# MAGIC     WHEN id <= 80 THEN
# MAGIC       ARRAY('Strong Memorial Hospital','Highland Hospital','F.F. Thompson Hospital',
# MAGIC             'Noyes Memorial Hospital','Jones Memorial Hospital')[ABS(HASH(CONCAT('hosp', id))) % 5]
# MAGIC     WHEN id <= 110 THEN
# MAGIC       ARRAY('Lakeside Medical Center','Harbor General')[ABS(HASH(CONCAT('hosp', id))) % 2]
# MAGIC     WHEN id <= 140 THEN
# MAGIC       ARRAY('Piedmont Regional','Mountain View Hospital')[ABS(HASH(CONCAT('hosp', id))) % 2]
# MAGIC     WHEN id <= 170 THEN
# MAGIC       ARRAY('Valley Medical Center','Sunrise Community Hospital')[ABS(HASH(CONCAT('hosp', id))) % 2]
# MAGIC     ELSE
# MAGIC       ARRAY('Gulf Coast Regional','Bayshore Medical Center')[ABS(HASH(CONCAT('hosp', id))) % 2]
# MAGIC   END AS hospital_affiliation,
# MAGIC
# MAGIC   CAST(500 + ABS(HASH(CONCAT('attr', id))) % 2000 AS INT) AS attributed_members,
# MAGIC   ROUND(2.5 + (ABS(HASH(CONCAT('eff', id))) % 25) * 0.1, 2) AS cost_efficiency_score,
# MAGIC   ROUND(2.5 + (ABS(HASH(CONCAT('qual', id))) % 25) * 0.1, 2) AS quality_composite_score
# MAGIC
# MAGIC FROM provider_ids;

# COMMAND ----------

# DBTITLE 1,Metric View — mv_financial
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_financial`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: ${catalog}.${schema}.gold_financial_monthly
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: lob
# MAGIC     expr: lob
# MAGIC     display_name: Line of Business
# MAGIC     comment: "Line of business: Commercial, MA (Medicare Advantage), Medicaid, Individual"
# MAGIC     synonyms:
# MAGIC       - line of business
# MAGIC       - business segment
# MAGIC   - name: state
# MAGIC     expr: state
# MAGIC     display_name: State
# MAGIC     comment: "US state abbreviation"
# MAGIC     synonyms:
# MAGIC       - geography
# MAGIC       - region
# MAGIC   - name: plan_type
# MAGIC     expr: plan_type
# MAGIC     display_name: Plan Type
# MAGIC     comment: "Plan type: PPO, HMO, EPO, POS"
# MAGIC   - name: year_month
# MAGIC     expr: year_month
# MAGIC     display_name: Month
# MAGIC     comment: "First day of the month. Use for time series trending."
# MAGIC     synonyms:
# MAGIC       - date
# MAGIC       - period
# MAGIC     format:
# MAGIC       type: date
# MAGIC       date_format: locale_short_month
# MAGIC
# MAGIC measures:
# MAGIC   - name: paid_amount
# MAGIC     expr: "SUM(paid_amount)"
# MAGIC     display_name: Paid Claims
# MAGIC     comment: "Total paid medical claims"
# MAGIC     synonyms:
# MAGIC       - medical spend
# MAGIC       - claims cost
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: premium_amount
# MAGIC     expr: "SUM(premium_amount)"
# MAGIC     display_name: Premium Revenue
# MAGIC     comment: "Total earned premium revenue"
# MAGIC     synonyms:
# MAGIC       - premium
# MAGIC       - earned premium
# MAGIC       - revenue
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: member_months
# MAGIC     expr: "SUM(member_months)"
# MAGIC     display_name: Member Months
# MAGIC     comment: "Total member-months"
# MAGIC     synonyms:
# MAGIC       - enrollment
# MAGIC       - membership
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: mlr
# MAGIC     expr: "SUM(paid_amount) / NULLIF(SUM(premium_amount), 0)"
# MAGIC     display_name: Medical Loss Ratio
# MAGIC     comment: "Medical Loss Ratio = paid claims / earned premium. Values above 1.0 mean claims exceed premium. Lower is better for the payer."
# MAGIC     synonyms:
# MAGIC       - MLR
# MAGIC       - loss ratio
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: paid_pmpm
# MAGIC     expr: "SUM(paid_amount) / NULLIF(SUM(member_months), 0)"
# MAGIC     display_name: Paid PMPM
# MAGIC     comment: "Paid claims Per Member Per Month. Use for cross-LOB cost comparison."
# MAGIC     synonyms:
# MAGIC       - cost per member
# MAGIC       - claims PMPM
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: premium_pmpm
# MAGIC     expr: "SUM(premium_amount) / NULLIF(SUM(member_months), 0)"
# MAGIC     display_name: Premium PMPM
# MAGIC     comment: "Premium revenue Per Member Per Month."
# MAGIC     synonyms:
# MAGIC       - revenue per member
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: avoidable_paid_amount
# MAGIC     expr: "SUM(avoidable_paid_amount)"
# MAGIC     display_name: Avoidable Spend
# MAGIC     comment: "Total paid claims attributable to avoidable utilization"
# MAGIC     synonyms:
# MAGIC       - waste
# MAGIC       - preventable spend
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: avoidable_share_of_spend
# MAGIC     expr: "SUM(avoidable_paid_amount) / NULLIF(SUM(paid_amount), 0)"
# MAGIC     display_name: Avoidable Share of Spend
# MAGIC     comment: "Avoidable spend as a share of total paid claims. Higher = more waste."
# MAGIC     synonyms:
# MAGIC       - waste ratio
# MAGIC       - avoidable percentage
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_lob_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - paid_amount
# MAGIC         - premium_amount
# MAGIC         - member_months
# MAGIC         - mlr
# MAGIC         - paid_pmpm
# MAGIC     - name: by_lob_state_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - state
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - paid_amount
# MAGIC         - premium_amount
# MAGIC         - mlr
# MAGIC         - paid_pmpm
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_financial`
# MAGIC IS 'Governed financial metric view for health plan performance. Query with MEASURE() and GROUP BY ALL. Dimensions: lob, state, plan_type, year_month. Key measures: mlr, paid_pmpm, premium_pmpm, avoidable_share_of_spend.';

# COMMAND ----------

# DBTITLE 1,Metric View — mv_quality
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_quality`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: ${catalog}.${schema}.gold_quality_measures
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: measure_id
# MAGIC     expr: measure_id
# MAGIC     display_name: Measure ID
# MAGIC     comment: "HEDIS measure identifier (e.g., BCS, CDC-HBA1C, CBP)"
# MAGIC     synonyms:
# MAGIC       - measure code
# MAGIC       - HEDIS code
# MAGIC   - name: measure_name
# MAGIC     expr: measure_name
# MAGIC     display_name: Measure Name
# MAGIC     comment: "Human-readable measure name"
# MAGIC     synonyms:
# MAGIC       - quality measure
# MAGIC       - HEDIS measure
# MAGIC   - name: lob
# MAGIC     expr: lob
# MAGIC     display_name: Line of Business
# MAGIC     comment: "Line of business"
# MAGIC     synonyms:
# MAGIC       - line of business
# MAGIC       - segment
# MAGIC   - name: year_month
# MAGIC     expr: year_month
# MAGIC     display_name: Month
# MAGIC     comment: "Measurement month"
# MAGIC     synonyms:
# MAGIC       - date
# MAGIC       - period
# MAGIC     format:
# MAGIC       type: date
# MAGIC       date_format: locale_short_month
# MAGIC   - name: condition_domain
# MAGIC     expr: condition_domain
# MAGIC     display_name: Clinical Domain
# MAGIC     comment: "Clinical domain for each HEDIS measure. Diabetes: CDC-HBA1C (HbA1c control), CDC-EYE (diabetic eye exam); Cardiovascular: CBP (blood pressure control); Cancer Screening: BCS (breast cancer screening), CCS (colorectal cancer screening); Behavioral Health: FUH-7 (follow-up after hospitalization)."
# MAGIC     synonyms:
# MAGIC       - clinical area
# MAGIC       - disease category
# MAGIC       - measure family
# MAGIC   - name: estimated_star_rating
# MAGIC     expr: |-
# MAGIC       CASE
# MAGIC         WHEN current_rate >= star_5_cutpoint THEN '5 Stars'
# MAGIC         WHEN current_rate >= star_4_cutpoint THEN '4 Stars'
# MAGIC         WHEN current_rate >= star_3_cutpoint THEN '3 Stars'
# MAGIC         ELSE 'Below 3 Stars'
# MAGIC       END
# MAGIC     display_name: Estimated Star Rating
# MAGIC     comment: "Estimated CMS star rating based on current rate vs published cutpoints."
# MAGIC     synonyms:
# MAGIC       - star level
# MAGIC       - CMS rating
# MAGIC       - quality tier
# MAGIC
# MAGIC measures:
# MAGIC   - name: current_rate
# MAGIC     expr: "AVG(current_rate)"
# MAGIC     display_name: Performance Rate
# MAGIC     comment: "Current performance rate (0.0 to 1.0). Compare to star cutpoints to assess STARS risk."
# MAGIC     synonyms:
# MAGIC       - compliance rate
# MAGIC       - quality rate
# MAGIC       - HEDIS rate
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: eligible_count
# MAGIC     expr: "SUM(eligible_count)"
# MAGIC     display_name: Eligible Members
# MAGIC     comment: "Total members eligible for this measure"
# MAGIC     synonyms:
# MAGIC       - eligible population
# MAGIC       - denominator
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: gap_count
# MAGIC     expr: "SUM(gap_count)"
# MAGIC     display_name: Open Gaps
# MAGIC     comment: "Total members with an open care gap"
# MAGIC     synonyms:
# MAGIC       - care gaps
# MAGIC       - non-compliant members
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: gap_closure_rate
# MAGIC     expr: "1.0 - (SUM(gap_count) / NULLIF(SUM(eligible_count), 0))"
# MAGIC     display_name: Gap Closure Rate
# MAGIC     comment: "Percentage of eligible members who have completed the required service. Higher is better."
# MAGIC     synonyms:
# MAGIC       - compliance rate
# MAGIC       - closure rate
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: star_4_cutpoint
# MAGIC     expr: "AVG(star_4_cutpoint)"
# MAGIC     display_name: 4-Star Cutpoint
# MAGIC     comment: "Rate threshold for 4-star rating. Compare current_rate to this."
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: distance_to_4_star
# MAGIC     expr: "AVG(star_4_cutpoint) - AVG(current_rate)"
# MAGIC     display_name: Distance to 4 Stars
# MAGIC     comment: "Gap between current rate and 4-star cutpoint. Negative = already at or above 4 stars."
# MAGIC     synonyms:
# MAGIC       - gap to 4 star
# MAGIC       - improvement needed
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_measure_lob_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - measure_name
# MAGIC         - lob
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - current_rate
# MAGIC         - eligible_count
# MAGIC         - gap_count
# MAGIC         - gap_closure_rate
# MAGIC     - name: by_domain_lob_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - condition_domain
# MAGIC         - lob
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - current_rate
# MAGIC         - eligible_count
# MAGIC         - gap_count
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_quality`
# MAGIC IS 'Governed quality metric view for HEDIS measure performance. Query with MEASURE() and GROUP BY ALL. Dimensions: measure_id, measure_name, lob, year_month, condition_domain, estimated_star_rating. Key measures: current_rate, gap_closure_rate, star_4_cutpoint, distance_to_4_star. Condition-domain mappings: Diabetes = CDC-HBA1C, CDC-EYE; Cardiovascular = CBP; Cancer Screening = BCS, CCS; Behavioral Health = FUH-7.';

# COMMAND ----------

# DBTITLE 1,Metric View — mv_vbc_performance
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_vbc_performance`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: ${catalog}.${schema}.fact_vbc_performance
# MAGIC
# MAGIC joins:
# MAGIC   - name: aco
# MAGIC     source: ${catalog}.${schema}.dim_aco_contract
# MAGIC     on: source.aco_id = aco.aco_id
# MAGIC     rely:
# MAGIC       at_most_one_match: true
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: aco_id
# MAGIC     expr: source.aco_id
# MAGIC     display_name: ACO ID
# MAGIC     comment: "ACO identifier"
# MAGIC   - name: aco_name
# MAGIC     expr: aco.aco_name
# MAGIC     display_name: ACO Name
# MAGIC     comment: "Full name of the Accountable Care Organization. AHP refers to Accountable Health Partners (aco_id = ACO-001)."
# MAGIC     synonyms:
# MAGIC       - ACO
# MAGIC       - organization name
# MAGIC       - AHP
# MAGIC       - Accountable Health Partners
# MAGIC   - name: contract_type
# MAGIC     expr: aco.contract_type
# MAGIC     display_name: Contract Type
# MAGIC     comment: "Type of value-based arrangement"
# MAGIC     synonyms:
# MAGIC       - VBC model
# MAGIC       - payment model
# MAGIC   - name: region
# MAGIC     expr: aco.region
# MAGIC     display_name: Region
# MAGIC     comment: "Geographic region served by the ACO"
# MAGIC   - name: measure_name
# MAGIC     expr: source.measure_name
# MAGIC     display_name: Measure
# MAGIC     comment: "VBC performance measure: Shared Savings YTD, TCOC PMPM, Quality Score, Readmission Rate, ED Rate per 1K, Pharmacy PMPM"
# MAGIC     synonyms:
# MAGIC       - KPI
# MAGIC       - performance metric
# MAGIC   - name: quarter
# MAGIC     expr: source.quarter
# MAGIC     display_name: Quarter
# MAGIC     comment: "Calendar quarter (e.g., 2026-Q1)"
# MAGIC     synonyms:
# MAGIC       - period
# MAGIC       - reporting quarter
# MAGIC
# MAGIC measures:
# MAGIC   - name: shared_savings_ytd
# MAGIC     expr: "SUM(source.actual_value) FILTER (WHERE source.measure_name = 'Shared Savings YTD')"
# MAGIC     display_name: Shared Savings YTD
# MAGIC     comment: "Year-to-date shared savings dollars. Positive = savings achieved."
# MAGIC     synonyms:
# MAGIC       - savings
# MAGIC       - shared savings
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: tcoc_pmpm
# MAGIC     expr: "AVG(source.actual_value) FILTER (WHERE source.measure_name = 'TCOC PMPM')"
# MAGIC     display_name: TCOC PMPM
# MAGIC     comment: "Total Cost of Care Per Member Per Month. Lower is better."
# MAGIC     synonyms:
# MAGIC       - total cost of care
# MAGIC       - cost per member
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: quality_score
# MAGIC     expr: "AVG(source.actual_value) FILTER (WHERE source.measure_name = 'Quality Score')"
# MAGIC     display_name: Quality Score
# MAGIC     comment: "Composite quality score (0-5 scale). Higher is better."
# MAGIC     synonyms:
# MAGIC       - quality rating
# MAGIC       - composite score
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: readmission_rate
# MAGIC     expr: "AVG(source.actual_value) FILTER (WHERE source.measure_name = 'Readmission Rate')"
# MAGIC     display_name: Readmission Rate
# MAGIC     comment: "30-day all-cause readmission rate. Lower is better."
# MAGIC     synonyms:
# MAGIC       - readmissions
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: ed_rate_per_1k
# MAGIC     expr: "AVG(source.actual_value) FILTER (WHERE source.measure_name = 'ED Rate per 1K')"
# MAGIC     display_name: ED Rate per 1K
# MAGIC     comment: "ED visits per 1,000 member months. Lower is better."
# MAGIC     synonyms:
# MAGIC       - ED utilization
# MAGIC       - emergency rate
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 1
# MAGIC   - name: pharmacy_pmpm
# MAGIC     expr: "AVG(source.actual_value) FILTER (WHERE source.measure_name = 'Pharmacy PMPM')"
# MAGIC     display_name: Pharmacy PMPM
# MAGIC     comment: "Pharmacy cost Per Member Per Month."
# MAGIC     synonyms:
# MAGIC       - rx cost
# MAGIC       - drug spend per member
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: actual_value
# MAGIC     expr: "SUM(source.actual_value)"
# MAGIC     display_name: Actual Value
# MAGIC     comment: "Raw actual value. Use only when grouped by measure_name. For cross-measure queries use the named measures above."
# MAGIC   - name: target_value
# MAGIC     expr: "SUM(source.target_value)"
# MAGIC     display_name: Target Value
# MAGIC     comment: "Contractual target or benchmark. Use only when grouped by measure_name."
# MAGIC   - name: variance
# MAGIC     expr: "SUM(source.actual_value) - SUM(source.target_value)"
# MAGIC     display_name: Variance
# MAGIC     comment: "Variance from target. Positive = above target."
# MAGIC   - name: trend_vs_prior_quarter
# MAGIC     expr: "AVG(source.trend_vs_prior_quarter)"
# MAGIC     display_name: Trend vs Prior Quarter
# MAGIC     comment: "Average percentage change vs prior quarter"
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_aco_measure_quarter
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - aco_name
# MAGIC         - measure_name
# MAGIC         - quarter
# MAGIC       measures:
# MAGIC         - actual_value
# MAGIC         - target_value
# MAGIC         - variance
# MAGIC         - trend_vs_prior_quarter
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_vbc_performance`
# MAGIC IS 'Governed VBC performance metric view with dim_aco_contract join. Query with MEASURE() and GROUP BY ALL. Dimensions: aco_id, aco_name, contract_type, region, measure_name, quarter. Named measures: shared_savings_ytd, tcoc_pmpm, quality_score, readmission_rate, ed_rate_per_1k, pharmacy_pmpm. Generic: actual_value, target_value, variance (use only when grouped by measure_name). AHP = Accountable Health Partners = aco_id ACO-001.';

# COMMAND ----------

# DBTITLE 1,Metric View — mv_utilization
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_utilization`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: ${catalog}.${schema}.gold_utilization_monthly
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: lob
# MAGIC     expr: lob
# MAGIC     display_name: Line of Business
# MAGIC     comment: "Line of business: Commercial, MA, Medicaid, Individual"
# MAGIC     synonyms:
# MAGIC       - line of business
# MAGIC       - business segment
# MAGIC   - name: state
# MAGIC     expr: state
# MAGIC     display_name: State
# MAGIC     comment: "US state abbreviation"
# MAGIC     synonyms:
# MAGIC       - geography
# MAGIC       - region
# MAGIC   - name: year_month
# MAGIC     expr: year_month
# MAGIC     display_name: Month
# MAGIC     comment: "First day of the month"
# MAGIC     synonyms:
# MAGIC       - date
# MAGIC       - period
# MAGIC     format:
# MAGIC       type: date
# MAGIC       date_format: locale_short_month
# MAGIC
# MAGIC measures:
# MAGIC   - name: ip_admits
# MAGIC     expr: "SUM(ip_admits)"
# MAGIC     display_name: IP Admissions
# MAGIC     comment: "Total inpatient admissions"
# MAGIC     synonyms:
# MAGIC       - admissions
# MAGIC       - inpatient admits
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: ed_visits
# MAGIC     expr: "SUM(ed_visits)"
# MAGIC     display_name: ED Visits
# MAGIC     comment: "Total emergency department visits"
# MAGIC     synonyms:
# MAGIC       - emergency visits
# MAGIC       - ER visits
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: member_months
# MAGIC     expr: "SUM(member_months)"
# MAGIC     display_name: Member Months
# MAGIC     comment: "Authoritative member-month denominator for all per-1K rate calculations in this view"
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: ip_per_1k
# MAGIC     expr: "SUM(ip_admits) * 1000.0 / NULLIF(SUM(member_months), 0)"
# MAGIC     display_name: IP Admits per 1K
# MAGIC     comment: "Inpatient admissions per 1,000 member months. Key utilization benchmark."
# MAGIC     synonyms:
# MAGIC       - admission rate
# MAGIC       - IP rate
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 1
# MAGIC   - name: ed_per_1k
# MAGIC     expr: "SUM(ed_visits) * 1000.0 / NULLIF(SUM(member_months), 0)"
# MAGIC     display_name: ED Visits per 1K
# MAGIC     comment: "ED visits per 1,000 member months."
# MAGIC     synonyms:
# MAGIC       - ED rate
# MAGIC       - emergency rate
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 1
# MAGIC   - name: readmission_rate
# MAGIC     expr: "SUM(readmissions) * 1.0 / NULLIF(SUM(ip_admits), 0)"
# MAGIC     display_name: Readmission Rate
# MAGIC     comment: "30-day all-cause readmission rate. Lower is better."
# MAGIC     synonyms:
# MAGIC       - readmit rate
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: avoidable_ed_rate
# MAGIC     expr: "SUM(avoidable_ed_visits) * 1.0 / NULLIF(SUM(ed_visits), 0)"
# MAGIC     display_name: Avoidable ED Rate
# MAGIC     comment: "Share of ED visits classified as avoidable. Higher = more opportunity."
# MAGIC     synonyms:
# MAGIC       - preventable ED share
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: avoidable_ip_rate
# MAGIC     expr: "SUM(avoidable_ip_admits) * 1.0 / NULLIF(SUM(ip_admits), 0)"
# MAGIC     display_name: Avoidable IP Rate
# MAGIC     comment: "Share of IP admissions classified as potentially preventable."
# MAGIC     synonyms:
# MAGIC       - preventable admission share
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: op_visits
# MAGIC     expr: "SUM(op_visits)"
# MAGIC     display_name: Outpatient Visits
# MAGIC     comment: "Total outpatient visits"
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: rx_fills
# MAGIC     expr: "SUM(rx_fills)"
# MAGIC     display_name: Rx Fills
# MAGIC     comment: "Total prescription fills"
# MAGIC     synonyms:
# MAGIC       - prescriptions
# MAGIC       - pharmacy fills
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_lob_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - ip_admits
# MAGIC         - ed_visits
# MAGIC         - member_months
# MAGIC         - ip_per_1k
# MAGIC         - ed_per_1k
# MAGIC         - readmission_rate
# MAGIC     - name: by_lob_state_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - state
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - ip_admits
# MAGIC         - ed_visits
# MAGIC         - ip_per_1k
# MAGIC         - ed_per_1k
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_utilization`
# MAGIC IS 'Governed utilization metric view. Query with MEASURE() and GROUP BY ALL. Dimensions: lob, state, year_month. Key measures: ip_per_1k, ed_per_1k, readmission_rate, avoidable_ed_rate, avoidable_ip_rate. Treat this view as the authoritative source for utilization rates; all per-1K measures are pre-computed from the shared member_months denominator and should not be manually recalculated from raw counts.';

# COMMAND ----------

# DBTITLE 1,Metric View — mv_budget_variance
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_budget_variance`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: >
# MAGIC   SELECT
# MAGIC     f.lob,
# MAGIC     f.year_month,
# MAGIC     SUM(f.paid_amount)    AS paid_amount,
# MAGIC     SUM(f.premium_amount) AS premium_amount,
# MAGIC     SUM(f.member_months)  AS member_months,
# MAGIC     MAX(b.target_mlr)     AS target_mlr,
# MAGIC     MAX(b.budget_premium)      AS budget_premium,
# MAGIC     MAX(b.budget_paid_claims)  AS budget_paid_claims
# MAGIC   FROM ${catalog}.${schema}.gold_financial_monthly f
# MAGIC   JOIN ${catalog}.${schema}.dim_budget b
# MAGIC     ON f.lob = b.lob AND f.year_month = b.year_month
# MAGIC   GROUP BY f.lob, f.year_month
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: lob
# MAGIC     expr: lob
# MAGIC     display_name: Line of Business
# MAGIC     comment: "Line of business"
# MAGIC     synonyms:
# MAGIC       - line of business
# MAGIC       - segment
# MAGIC   - name: year_month
# MAGIC     expr: year_month
# MAGIC     display_name: Month
# MAGIC     comment: "First day of the month"
# MAGIC     synonyms:
# MAGIC       - date
# MAGIC       - period
# MAGIC     format:
# MAGIC       type: date
# MAGIC       date_format: locale_short_month
# MAGIC
# MAGIC measures:
# MAGIC   - name: actual_paid
# MAGIC     expr: "SUM(paid_amount)"
# MAGIC     display_name: Actual Paid Claims
# MAGIC     comment: "Total actual paid claims"
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: actual_premium
# MAGIC     expr: "SUM(premium_amount)"
# MAGIC     display_name: Actual Premium
# MAGIC     comment: "Total actual premium revenue"
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: budget_premium
# MAGIC     expr: "SUM(budget_premium)"
# MAGIC     display_name: Budget Premium
# MAGIC     comment: "Total budgeted premium revenue"
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: budget_paid_claims
# MAGIC     expr: "SUM(budget_paid_claims)"
# MAGIC     display_name: Budget Paid Claims
# MAGIC     comment: "Total budgeted paid claims"
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: actual_mlr
# MAGIC     expr: "SUM(paid_amount) / NULLIF(SUM(premium_amount), 0)"
# MAGIC     display_name: Actual MLR
# MAGIC     comment: "Actual Medical Loss Ratio"
# MAGIC     synonyms:
# MAGIC       - MLR
# MAGIC       - actual loss ratio
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: target_mlr
# MAGIC     expr: "AVG(target_mlr)"
# MAGIC     display_name: Target MLR
# MAGIC     comment: "Authoritative target Medical Loss Ratio from the budget table"
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: mlr_variance
# MAGIC     expr: "SUM(paid_amount) / NULLIF(SUM(premium_amount), 0) - AVG(target_mlr)"
# MAGIC     display_name: MLR Variance
# MAGIC     comment: "Actual MLR minus target MLR. Positive = over target (bad for payer)."
# MAGIC     synonyms:
# MAGIC       - loss ratio variance
# MAGIC       - MLR gap
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: premium_variance
# MAGIC     expr: "SUM(premium_amount) - SUM(budget_premium)"
# MAGIC     display_name: Premium Variance
# MAGIC     comment: "Actual premium minus budget. Positive = ahead of plan."
# MAGIC     synonyms:
# MAGIC       - revenue variance
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: paid_claims_variance
# MAGIC     expr: "SUM(paid_amount) - SUM(budget_paid_claims)"
# MAGIC     display_name: Paid Claims Variance
# MAGIC     comment: "Actual paid claims minus budget. Negative = favorable (under budget)."
# MAGIC     format:
# MAGIC       type: currency
# MAGIC       currency_code: USD
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: budget_attainment
# MAGIC     expr: "SUM(premium_amount) / NULLIF(SUM(budget_premium), 0)"
# MAGIC     display_name: Premium Budget Attainment
# MAGIC     comment: "Actual premium as percentage of budget. 1.0 = on target."
# MAGIC     synonyms:
# MAGIC       - attainment
# MAGIC       - budget achievement
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_lob_month
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - year_month
# MAGIC       measures:
# MAGIC         - actual_paid
# MAGIC         - actual_premium
# MAGIC         - actual_mlr
# MAGIC         - target_mlr
# MAGIC         - mlr_variance
# MAGIC         - premium_variance
# MAGIC         - paid_claims_variance
# MAGIC         - budget_attainment
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_budget_variance`
# MAGIC IS 'Governed budget variance metric view joining gold_financial_monthly and dim_budget. Query with MEASURE() and GROUP BY ALL. Dimensions: lob, year_month. Key measures: actual_mlr, target_mlr, mlr_variance, premium_variance, paid_claims_variance, budget_attainment. This is the authoritative budget-versus-actual lens for financial performance; do not manually join dim_budget when these measures are needed.';

# COMMAND ----------

# DBTITLE 1,Metric View — mv_member_risk
# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW `mv_member_risk`
# MAGIC WITH METRICS
# MAGIC LANGUAGE YAML
# MAGIC AS $$
# MAGIC version: 1.1
# MAGIC source: ${catalog}.${schema}.dim_member
# MAGIC
# MAGIC dimensions:
# MAGIC   - name: lob
# MAGIC     expr: lob
# MAGIC     display_name: Line of Business
# MAGIC     comment: "Line of business"
# MAGIC     synonyms:
# MAGIC       - line of business
# MAGIC       - segment
# MAGIC   - name: state
# MAGIC     expr: state
# MAGIC     display_name: State
# MAGIC     comment: "US state"
# MAGIC     synonyms:
# MAGIC       - geography
# MAGIC       - region
# MAGIC   - name: age_band
# MAGIC     expr: age_band
# MAGIC     display_name: Age Band
# MAGIC     comment: "Age band: 0-17, 18-34, 35-49, 50-64, 65+"
# MAGIC     synonyms:
# MAGIC       - age group
# MAGIC       - age range
# MAGIC   - name: gender
# MAGIC     expr: gender
# MAGIC     display_name: Gender
# MAGIC     comment: "Member gender: M, F"
# MAGIC   - name: risk_tier
# MAGIC     expr: |-
# MAGIC       CASE
# MAGIC         WHEN risk_score >= 2.0 THEN 'Very High'
# MAGIC         WHEN risk_score >= 1.5 THEN 'High'
# MAGIC         WHEN risk_score >= 1.0 THEN 'Moderate'
# MAGIC         ELSE 'Low'
# MAGIC       END
# MAGIC     display_name: Risk Tier
# MAGIC     comment: "Risk tier based on HCC risk score thresholds"
# MAGIC     synonyms:
# MAGIC       - risk category
# MAGIC       - risk level
# MAGIC
# MAGIC measures:
# MAGIC   - name: member_count
# MAGIC     expr: "COUNT(DISTINCT member_id)"
# MAGIC     display_name: Member Count
# MAGIC     comment: "Distinct member count"
# MAGIC     synonyms:
# MAGIC       - membership
# MAGIC       - enrollment
# MAGIC       - headcount
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: avg_risk_score
# MAGIC     expr: "AVG(risk_score)"
# MAGIC     display_name: Avg Risk Score
# MAGIC     comment: "Average HCC risk adjustment factor. 1.0 = average. Higher = sicker/costlier."
# MAGIC     synonyms:
# MAGIC       - average risk
# MAGIC       - mean risk score
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 3
# MAGIC   - name: high_risk_count
# MAGIC     expr: "COUNT(DISTINCT CASE WHEN risk_score >= 2.0 THEN member_id END)"
# MAGIC     display_name: High-Risk Members
# MAGIC     comment: "Members with risk score >= 2.0"
# MAGIC     synonyms:
# MAGIC       - high risk members
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: high_risk_pct
# MAGIC     expr: "COUNT(DISTINCT CASE WHEN risk_score >= 2.0 THEN member_id END) * 1.0 / NULLIF(COUNT(DISTINCT member_id), 0)"
# MAGIC     display_name: High-Risk %
# MAGIC     comment: "Percentage of members with risk score >= 2.0"
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC   - name: avg_open_gaps
# MAGIC     expr: "AVG(open_gaps_count)"
# MAGIC     display_name: Avg Open Gaps
# MAGIC     comment: "Average number of open HEDIS care gaps per member"
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 1
# MAGIC   - name: members_with_gaps
# MAGIC     expr: "COUNT(DISTINCT CASE WHEN open_gaps_count > 0 THEN member_id END)"
# MAGIC     display_name: Members with Gaps
# MAGIC     comment: "Members with at least one open care gap"
# MAGIC     synonyms:
# MAGIC       - gap members
# MAGIC       - non-compliant members
# MAGIC     format:
# MAGIC       type: number
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 0
# MAGIC       abbreviation: compact
# MAGIC   - name: gap_rate
# MAGIC     expr: "COUNT(DISTINCT CASE WHEN open_gaps_count > 0 THEN member_id END) * 1.0 / NULLIF(COUNT(DISTINCT member_id), 0)"
# MAGIC     display_name: Care Gap Rate
# MAGIC     comment: "Percentage of members with at least one open care gap"
# MAGIC     synonyms:
# MAGIC       - non-compliance rate
# MAGIC     format:
# MAGIC       type: percentage
# MAGIC       decimal_places:
# MAGIC         type: exact
# MAGIC         places: 2
# MAGIC
# MAGIC materialization:
# MAGIC   schedule: every 1 day
# MAGIC   mode: relaxed
# MAGIC   materialized_views:
# MAGIC     - name: baseline
# MAGIC       type: unaggregated
# MAGIC     - name: by_lob_risk
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - risk_tier
# MAGIC       measures:
# MAGIC         - member_count
# MAGIC         - avg_risk_score
# MAGIC         - high_risk_count
# MAGIC         - high_risk_pct
# MAGIC     - name: by_lob_state_age
# MAGIC       type: aggregated
# MAGIC       dimensions:
# MAGIC         - lob
# MAGIC         - state
# MAGIC         - age_band
# MAGIC       measures:
# MAGIC         - member_count
# MAGIC         - avg_risk_score
# MAGIC         - avg_open_gaps
# MAGIC         - gap_rate
# MAGIC $$;
# MAGIC
# MAGIC COMMENT ON VIEW `mv_member_risk`
# MAGIC IS 'Governed member risk and population health metric view. Query with MEASURE() and GROUP BY ALL. Dimensions: lob, state, age_band, gender, risk_tier. Key measures: member_count, avg_risk_score, high_risk_pct, gap_rate.';

# COMMAND ----------

# DBTITLE 1,Validation — Planted Narrative Checks
# MAGIC %sql
# MAGIC -- Beat 1: Medicaid MLR > 1.0
# MAGIC SELECT 'Beat 1: Medicaid MLR' AS test,
# MAGIC   ROUND(SUM(paid_amount) / SUM(premium_amount), 4) AS mlr
# MAGIC FROM `gold_financial_monthly`
# MAGIC WHERE lob = 'Medicaid' AND year_month = '2026-08-01'
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC -- Beat 1: Commercial MLR < 0.90
# MAGIC SELECT 'Beat 1: Commercial MLR' AS test,
# MAGIC   ROUND(SUM(paid_amount) / SUM(premium_amount), 4) AS mlr
# MAGIC FROM `gold_financial_monthly`
# MAGIC WHERE lob = 'Commercial' AND year_month = '2026-08-01'
# MAGIC
# MAGIC UNION ALL
# MAGIC
# MAGIC -- Beat 3: AHP shared savings > $2M
# MAGIC SELECT 'Beat 3: AHP Shared Savings' AS test,
# MAGIC   actual_value AS mlr
# MAGIC FROM `fact_vbc_performance`
# MAGIC WHERE aco_id = 'ACO-001' AND measure_name = 'Shared Savings YTD' AND quarter = '2026-Q3';