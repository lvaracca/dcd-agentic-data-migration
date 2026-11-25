-- =============================================================================
-- UrbanFork OLTP Source Schema (Synced Incrementally via Airbyte)
-- High-watermark cursor aligns with historical dataset cutoff (2026-03-31)
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS oltp;

CREATE TABLE IF NOT EXISTS oltp.dlv_ord_hdr (
    ord_id VARCHAR(24) PRIMARY KEY,
    ord_dt_sk INTEGER NOT NULL,
    ord_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    usr_id VARCHAR(24) NOT NULL,
    mrc_id VARCHAR(20) NOT NULL,
    crr_id VARCHAR(20) NOT NULL,
    zone_id VARCHAR(20) NOT NULL,
    vert_cd INTEGER NOT NULL,
    ord_sts_cd VARCHAR(4) NOT NULL,
    dlv_fee_usd NUMERIC(10, 2) NOT NULL,
    srv_fee_usd NUMERIC(10, 2) NOT NULL,
    tip_usd NUMERIC(10, 2) NOT NULL,
    crr_pay_usd NUMERIC(10, 2) NOT NULL,
    promo_voucher_usd NUMERIC(10, 2) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.dlv_ord_item_ln (
    ord_ln_id VARCHAR(24) PRIMARY KEY,
    ord_id VARCHAR(24) NOT NULL REFERENCES oltp.dlv_ord_hdr(ord_id),
    item_sku VARCHAR(20) NOT NULL,
    item_nm VARCHAR(120) NOT NULL,
    qty_n INTEGER NOT NULL,
    unit_prc_usd NUMERIC(10, 2) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.dsp_refund_fct (
    dsp_id VARCHAR(24) PRIMARY KEY,
    ord_id VARCHAR(24) NOT NULL REFERENCES oltp.dlv_ord_hdr(ord_id),
    dsp_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    rfnd_amt_usd NUMERIC(10, 2) NOT NULL,
    rfnd_sts_flg INTEGER NOT NULL,
    dsp_rsn_cd INTEGER NOT NULL,
    cust_ticket_txt VARCHAR(1000),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ord_updated_at ON oltp.dlv_ord_hdr(updated_at);
CREATE INDEX IF NOT EXISTS idx_ln_updated_at ON oltp.dlv_ord_item_ln(updated_at);
CREATE INDEX IF NOT EXISTS idx_dsp_updated_at ON oltp.dsp_refund_fct(updated_at);

-- Seed watermark anchor record matching historical cutoff (ORD-0090000 @ 2026-03-31)
INSERT INTO oltp.dlv_ord_hdr VALUES (
    'ORD-0090000', 20260331, '2026-03-31 23:58:00', 'USR-000100', 'MRC-0001',
    'CRR-00010', 'ZNE-LON-01', 1, 'D', 3.99, 2.48, 3.00, 5.25, 0.00, '2026-03-31 23:58:00'
) ON CONFLICT DO NOTHING;

INSERT INTO oltp.dlv_ord_item_ln VALUES (
    'LN-00277146', 'ORD-0090000', 'SKU-R01', 'Double Smash Burger', 2, 15.50, '2026-03-31 23:58:00'
) ON CONFLICT DO NOTHING;
