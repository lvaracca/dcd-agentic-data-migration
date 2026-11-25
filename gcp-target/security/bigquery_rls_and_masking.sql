-- =============================================================================
-- UrbanFork BigQuery Governance Migration (from Snowflake Horizon Policies)
-- Translates:
--   * GOVERNANCE.RAP_REGIONAL_ZONE_ACCESS -> BigQuery Row Access Policy (RLS)
--   * GOVERNANCE.MSK_EMAIL_POLICY / MSK_PHONE_POLICY -> BigQuery Policy Tags (CLS)
-- =============================================================================

-- 1. Regional Row Access Policy on GEO_ZONE_LKP (mirrors Snowflake RAP_REGIONAL_ZONE_ACCESS)
CREATE OR REPLACE ROW ACCESS POLICY rap_admin_full_access
ON `dcd-migration-demo.urbanfork_raw_ops.GEO_ZONE_LKP`
GRANT TO ("user:admin@lvaracca.altostrat.com", "serviceAccount:quickbite-airbyte-sa@dcd-migration-demo.iam.gserviceaccount.com")
FILTER USING (TRUE);

-- Example regional analyst policies (bind to Google Groups in production):
-- CREATE OR REPLACE ROW ACCESS POLICY `dcd-migration-demo.urbanfork_raw_ops.GEO_ZONE_LKP.rap_emea_analysts`
-- ON `dcd-migration-demo.urbanfork_raw_ops.GEO_ZONE_LKP`
-- GRANT TO ("group:uf-analysts-emea@urbanfork.example.com")
-- FILTER USING (REG_CD = 'EMEA');

-- 2. Column-Level Security & Data Masking (Data Catalog Policy Tags Blueprint)
-- Replaces Snowflake GOVERNANCE.MSK_EMAIL_POLICY & GOVERNANCE.MSK_PHONE_POLICY:
--   Taxonomy: UrbanFork_PII_Taxonomy (location: us-central1)
--   - Policy Tag `CONFIDENTIAL_PII` (Masking Rule: DEFAULT_MASKING_VALUE / SHA256)
--       -> Applied to `dcd-migration-demo.urbanfork_raw_ops.CUST_USER_MSTR.EMAIL_TXT`
--   - Policy Tag `RESTRICTED_CONTACT` (Masking Rule: LAST_FOUR_CHARACTERS)
--       -> Applied to `dcd-migration-demo.urbanfork_raw_ops.CUST_USER_MSTR.PHONE_TXT`
--       -> Applied to `dcd-migration-demo.urbanfork_raw_ops.CRR_COURIER_MSTR.PHONE_TXT`
