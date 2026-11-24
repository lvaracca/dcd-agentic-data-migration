const rawOpsTables = [
  "DLV_ORD_HDR",
  "DLV_ORD_ITEM_LN",
  "ZNE_FLEET_SNAP",
  "MRC_PAYOUT_LEDGER",
  "SYS_CAL_DIM",
  "GEO_ZONE_LKP",
  "MRC_PARTNER_MSTR",
  "MRC_COMM_SCD2",
  "CUST_USER_MSTR",
  "CRR_COURIER_MSTR",
  "DSP_REFUND_FCT"
];

rawOpsTables.forEach((name) => {
  declare({
    database: dataform.projectConfig.defaultDatabase,
    schema: dataform.projectConfig.vars.rawOpsDataset,
    name: name
  });
});

declare({
  database: dataform.projectConfig.defaultDatabase,
  schema: dataform.projectConfig.vars.rawIotDataset,
  name: "APP_DELIVERY_PINGS"
});
