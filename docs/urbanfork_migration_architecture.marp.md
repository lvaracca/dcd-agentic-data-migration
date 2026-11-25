---
marp: true
theme: default
size: 16:9
paginate: true
header: "UrbanFork — Migration Snowflake vers Google Cloud"
footer: "Architecture, Objectifs KPI & Données Synthétiques | Antigravity Demo"
style: |
  section {
    font-family: 'Inter', 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 21px;
    color: #202124;
    background-color: #ffffff;
    padding: 46px 56px 44px 56px;
  }
  header, footer {
    font-size: 12px;
    color: #5f6368;
  }
  h1 {
    color: #1a73e8;
    font-size: 36px;
    margin-bottom: 14px;
    border-bottom: 3px solid #e8f0fe;
    padding-bottom: 8px;
  }
  h2 {
    color: #174ea6;
    font-size: 24px;
    margin-top: 10px;
    margin-bottom: 8px;
  }
  h3 {
    color: #202124;
    font-size: 19px;
    margin: 6px 0;
  }
  section.lead {
    background: linear-gradient(135deg, #0d2b5c 0%, #1a73e8 60%, #185abc 100%);
    color: #ffffff;
    justify-content: center;
  }
  section.lead h1 {
    color: #ffffff;
    font-size: 46px;
    border-bottom: none;
    margin-bottom: 12px;
  }
  section.lead h2 {
    color: #d2e3fc;
    font-size: 24px;
    font-weight: 400;
  }
  section.lead p, section.lead li {
    color: #e8f0fe;
  }
  section.lead header, section.lead footer {
    color: #aecbfa;
  }
  .cols-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    align-items: start;
  }
  .cols-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 18px;
    align-items: stretch;
  }
  .card {
    background: #f8f9fa;
    border: 1px solid #dadce0;
    border-radius: 10px;
    padding: 16px 18px;
  }
  .card-blue {
    background: #e8f0fe;
    border-left: 5px solid #1a73e8;
    border-radius: 8px;
    padding: 14px 18px;
  }
  .card-green {
    background: #e6f4ea;
    border-left: 5px solid #137333;
    border-radius: 8px;
    padding: 14px 18px;
  }
  .card-red {
    background: #fce8e6;
    border-left: 5px solid #c5221f;
    border-radius: 8px;
    padding: 14px 18px;
  }
  .card-yellow {
    background: #fef7e0;
    border-left: 5px solid #f29900;
    border-radius: 8px;
    padding: 14px 18px;
  }
  .kpi-num {
    font-size: 32px;
    font-weight: 700;
    color: #1a73e8;
    line-height: 1.1;
  }
  .kpi-num-green {
    font-size: 30px;
    font-weight: 700;
    color: #137333;
    line-height: 1.1;
  }
  .kpi-num-red {
    font-size: 28px;
    font-weight: 700;
    color: #c5221f;
    line-height: 1.1;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14.5px;
    margin-top: 8px;
  }
  th {
    background: #1a73e8;
    color: #ffffff;
    text-align: left;
    padding: 7px 9px;
  }
  td {
    padding: 6px 9px;
    border-bottom: 1px solid #e0e0e0;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #f8f9fa;
  }
  code {
    background: #f1f3f4;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.88em;
    color: #174ea6;
  }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }
  .b-ice { background: #e8f0fe; color: #1967d2; }
  .b-fdn { background: #fef7e0; color: #b06000; }
  .b-iot { background: #f3e8fd; color: #7627bb; }
  .small { font-size: 16px; color: #5f6368; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# UrbanFork : Migration Snowflake vers Google Cloud

## Remplacer le cœur analytique sans disruption et sacraliser les KPIs métier avec Antigravity

<br>

- **Scénario** : Plateforme de livraison repas & courses à la demande (*UrbanFork*)
- **Périmètre Live** : `Airbyte -> Snowflake (Iceberg + FDN + Tasks) -> Power BI` basculé vers `BigLake + BigQuery + Dataform + Spark + BQ AI + Knowledge Catalog`
- **Format de la démonstration** : 45 minutes, 100 % exécuté en direct sur GCP (`us-central1`)

---

# 1. L'Objectif : Deux Impératifs Indissociables

Une migration d'entrepôt de données ne se résume jamais à déplacer des tables. Snowflake vit au centre d'un écosystème opérationnel et décisionnel actif.

<div class="cols-2">
<div class="card-blue">

### Impératif A — Remplacer sans disruption
- **En amont (Ingestion)** : basculer **Airbyte** de Snowflake vers BigQuery en conservant les curseurs incrémentaux (`updated_at`), sans perdre une seule commande live.
- **Au centre (Stockage & DAG)** : monter les tables **Apache Iceberg** en *Zero-Copy* (**BigLake**), migrer les 7 **Snowflake Tasks** vers **Dataform**, et moderniser Snowpark & Cortex vers **Managed Spark** & **BigQuery AI**.
- **En aval (BI)** : rebrancher **Power BI** (`.pbip` / `.tmdl`) sur BigQuery sans casser une seule mesure DAX ni un seul graphique.

</div>
<div class="card-green">

### Impératif B — Sacraliser les KPIs métier
- **Sortir du "tribal knowledge"** : aujourd'hui, les règles de calcul sont éparpillées entre vues SQL, scripts Python, YAML et formules DAX Power BI.
- **Knowledge-as-Code (`OKF v0.2`)** : rétro-ingénierie automatisée de toutes les formules, codes statuts et pièges de jointure vers **Google Cloud Knowledge Catalog**.
- **Vérité unique & vérifiable** :
  - Parité **au centime près** entre Snowflake et BigQuery (`verify_migration_parity.py`).
  - Même chiffre dans **Power BI** et **BigQuery Conversational Analytics**.

</div>
</div>

---

# 2. Architecture Globale : Avant (Legacy) vs. Après (GCP)

<svg viewBox="0 0 1120 470" width="100%" height="440" xmlns="http://www.w3.org/2000/svg" style="font-family: Inter, Arial, sans-serif;">
  <!-- Upstream -->
  <rect x="10" y="120" width="205" height="230" rx="12" fill="#f8f9fa" stroke="#5f6368" stroke-width="1.5"/>
  <text x="112" y="146" text-anchor="middle" font-size="14" font-weight="700" fill="#202124">AMONT (VM Privée GCE)</text>
  <rect x="26" y="165" width="173" height="62" rx="8" fill="#ffffff" stroke="#1a73e8" stroke-width="1.5"/>
  <text x="112" y="191" text-anchor="middle" font-size="13" font-weight="700" fill="#174ea6">PostgreSQL OLTP</text>
  <text x="112" y="211" text-anchor="middle" font-size="11.5" fill="#5f6368">urbanfork_oltp (:5439)</text>
  <line x1="112" y1="227" x2="112" y2="255" stroke="#5f6368" stroke-width="2"/>
  <polygon points="107,252 117,252 112,262" fill="#5f6368"/>
  <rect x="26" y="264" width="173" height="70" rx="8" fill="#e8f0fe" stroke="#1a73e8" stroke-width="2"/>
  <text x="112" y="290" text-anchor="middle" font-size="13" font-weight="700" fill="#174ea6">Airbyte OSS v2.5</text>
  <text x="112" y="309" text-anchor="middle" font-size="11" fill="#3c4043">Sync incrémental CDC_</text>
  <text x="112" y="324" text-anchor="middle" font-size="10.5" fill="#137333">Tunnel IAP • ADC Keyless</text>

  <!-- Legacy Snowflake -->
  <rect x="275" y="15" width="560" height="165" rx="12" fill="#fce8e6" stroke="#c5221f" stroke-width="1.5" stroke-dasharray="6,4"/>
  <text x="295" y="39" font-size="13.5" font-weight="700" fill="#a50e0e">AVANT — Legacy Snowflake (URBANFORK_PROD • GCP us-central1)</text>
  <rect x="292" y="54" width="165" height="108" rx="8" fill="#ffffff" stroke="#d93025"/>
  <text x="374" y="77" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">OPS_RAW &amp; IOT_RAW</text>
  <text x="374" y="98" text-anchor="middle" font-size="11" fill="#5f6368">4 Tables Iceberg (GCS)</text>
  <text x="374" y="116" text-anchor="middle" font-size="11" fill="#5f6368">7 Tables FDN + Mask/RLS</text>
  <text x="374" y="134" text-anchor="middle" font-size="11" fill="#5f6368">1 Table VARIANT + Pipe</text>

  <rect x="478" y="54" width="175" height="108" rx="8" fill="#ffffff" stroke="#d93025"/>
  <text x="565" y="77" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">Compute &amp; Orchestrateur</text>
  <text x="565" y="98" text-anchor="middle" font-size="11" fill="#5f6368">7-Node Task DAG + Streams</text>
  <text x="565" y="116" text-anchor="middle" font-size="11" fill="#5f6368">Dynamic Table + Stored Proc</text>
  <text x="565" y="134" text-anchor="middle" font-size="11" fill="#5f6368">Snowpark Python + Cortex</text>

  <rect x="674" y="54" width="146" height="108" rx="8" fill="#ffffff" stroke="#d93025"/>
  <text x="747" y="77" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">MART (Gold)</text>
  <text x="747" y="99" text-anchor="middle" font-size="10.5" fill="#5f6368">FCT_PLATFORM_NET_REV</text>
  <text x="747" y="117" text-anchor="middle" font-size="10.5" fill="#5f6368">DIM_PRIME_PARTNER</text>
  <text x="747" y="135" text-anchor="middle" font-size="10.5" fill="#5f6368">DT_LIVE_ZONE_DEFICIT</text>

  <line x1="457" y1="108" x2="473" y2="108" stroke="#c5221f" stroke-width="2"/>
  <line x1="653" y1="108" x2="669" y2="108" stroke="#c5221f" stroke-width="2"/>

  <!-- Target GCP -->
  <rect x="275" y="210" width="560" height="245" rx="12" fill="#e6f4ea" stroke="#137333" stroke-width="2"/>
  <text x="295" y="235" font-size="13.5" font-weight="700" fill="#137333">APRÈS — Plateforme Cible Google Cloud (dcd-migration-demo • us-central1)</text>
  <rect x="292" y="250" width="165" height="110" rx="8" fill="#ffffff" stroke="#137333"/>
  <text x="374" y="273" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">BigQuery Raw Layer</text>
  <text x="374" y="294" text-anchor="middle" font-size="11" fill="#137333" font-weight="600">Zero-Copy BigLake Iceberg</text>
  <text x="374" y="312" text-anchor="middle" font-size="11" fill="#5f6368">Tables natives + JSON natif</text>
  <text x="374" y="330" text-anchor="middle" font-size="11" fill="#5f6368">Policy Tags (CLS) &amp; RLS</text>

  <rect x="478" y="250" width="175" height="110" rx="8" fill="#ffffff" stroke="#137333"/>
  <text x="565" y="273" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">Dataform, Spark &amp; AI</text>
  <text x="565" y="294" text-anchor="middle" font-size="11" fill="#5f6368">DAG Dataform (.sqlx) + Tests</text>
  <text x="565" y="312" text-anchor="middle" font-size="11" fill="#5f6368">Managed Spark (Dataproc)</text>
  <text x="565" y="330" text-anchor="middle" font-size="11" fill="#5f6368">BigQuery AI (Gemini/TimesFM)</text>

  <rect x="674" y="250" width="146" height="110" rx="8" fill="#ffffff" stroke="#137333"/>
  <text x="747" y="273" text-anchor="middle" font-size="12.5" font-weight="700" fill="#202124">urbanfork_gold_mart</text>
  <text x="747" y="294" text-anchor="middle" font-size="10.5" fill="#137333" font-weight="600">Contrat 100 % identique</text>
  <text x="747" y="312" text-anchor="middle" font-size="10.5" fill="#5f6368">Colonnes MAJUSCULES</text>
  <text x="747" y="330" text-anchor="middle" font-size="10.5" fill="#5f6368">Parité vérifiée au centime</text>

  <rect x="292" y="375" width="528" height="64" rx="8" fill="#fef7e0" stroke="#f29900" stroke-width="1.5"/>
  <text x="556" y="399" text-anchor="middle" font-size="13" font-weight="700" fill="#b06000">Knowledge Catalog &amp; Open Knowledge Format (OKF v0.2)</text>
  <text x="556" y="421" text-anchor="middle" font-size="11.5" fill="#3c4043">Règles extraites de SQL + Python + DAX • Glossary • Context Set • Usage-Based Joins (QUERY_HISTORY)</text>

  <line x1="457" y1="305" x2="473" y2="305" stroke="#137333" stroke-width="2"/>
  <line x1="653" y1="305" x2="669" y2="305" stroke="#137333" stroke-width="2"/>

  <!-- Downstream -->
  <rect x="890" y="95" width="220" height="295" rx="12" fill="#f8f9fa" stroke="#5f6368" stroke-width="1.5"/>
  <text x="1000" y="122" text-anchor="middle" font-size="14" font-weight="700" fill="#202124">AVAL (BI &amp; IA Métier)</text>
  <rect x="906" y="145" width="188" height="96" rx="8" fill="#ffffff" stroke="#f29900" stroke-width="2"/>
  <text x="1000" y="172" text-anchor="middle" font-size="13" font-weight="700" fill="#b06000">Power BI (.pbip / TMDL)</text>
  <text x="1000" y="193" text-anchor="middle" font-size="11" fill="#5f6368">11 mesures DAX intactes</text>
  <text x="1000" y="211" text-anchor="middle" font-size="11" fill="#137333" font-weight="600">GoogleBigQuery.Database()</text>
  <text x="1000" y="227" text-anchor="middle" font-size="10.5" fill="#5f6368">DirectQuery Storage API</text>

  <rect x="906" y="268" width="188" height="96" rx="8" fill="#e8f0fe" stroke="#1a73e8" stroke-width="2"/>
  <text x="1000" y="294" text-anchor="middle" font-size="13" font-weight="700" fill="#174ea6">Conversational Analytics</text>
  <text x="1000" y="315" text-anchor="middle" font-size="11" fill="#3c4043">Q&amp;A en langage naturel</text>
  <text x="1000" y="333" text-anchor="middle" font-size="11" fill="#3c4043">Ancré sur Knowledge Catalog</text>
  <text x="1000" y="350" text-anchor="middle" font-size="10.5" fill="#137333">Zéro piège SCD2 / Snapshot</text>

  <!-- Cutover Arrows -->
  <path d="M 199 285 C 235 285, 235 108, 286 108" fill="none" stroke="#c5221f" stroke-width="2" stroke-dasharray="5,4"/>
  <path d="M 199 305 L 286 305" fill="none" stroke="#137333" stroke-width="3"/>
  <polygon points="282,299 292,305 282,311" fill="#137333"/>

  <path d="M 820 108 C 858 108, 860 180, 900 180" fill="none" stroke="#c5221f" stroke-width="2" stroke-dasharray="5,4"/>
  <path d="M 820 295 C 860 295, 860 205, 900 205" fill="none" stroke="#137333" stroke-width="3"/>
  <polygon points="896,199 906,205 896,211" fill="#137333"/>

  <path d="M 820 407 C 865 407, 865 320, 900 320" fill="none" stroke="#1a73e8" stroke-width="3"/>
  <polygon points="896,314 906,320 896,326" fill="#1a73e8"/>
</svg>

---

# 3. Infrastructure Live & Choix d'Architecture GCP

Tout l'environnement est déployé en **`us-central1`** (co-localisation Snowflake Trial, GCS, BigQuery, Dataform et Airbyte) dans le projet **`dcd-migration-demo`**.

<div class="cols-2">
<div class="card">

### Ingestion Sécurisée (Option A)
- **VM GCE privée** `quickbite-airbyte-vm` (`e2-standard-4`, Shielded VM, **aucune IP publique**).
- Sortie Internet via **Cloud Router + Cloud NAT**, accès admin/UI uniquement via **tunnel IAP** (`localhost:8000`).
- **PostgreSQL OLTP** (`urbanfork-oltp-postgres`) + **Airbyte OSS v2.5** (`abctl` / `kind`).
- **Zéro clé JSON** : Airbyte écrit dans BigQuery via l'**ADC natif** du Service Account `quickbite-airbyte-sa`.

</div>
<div class="card">

### Stockage Hybride & Gouvernance
- **Bucket Lakehouse** `gs://dcd-migration-demo-urbanfork-lakehouse` hébergeant les fichiers Parquet/Metadata des **4 tables Apache Iceberg** écrites par Snowflake.
- **Connexion BigLake** (`biglake-iceberg-conn`) permettant le montage *Zero-Copy* immédiat dans `urbanfork_raw_ops`.
- **Sécurité équivalente** :
  - Snowflake *Dynamic Masking* -> BigQuery **Policy Tags (CLS)**.
  - Snowflake *Row Access Policy* (`REG_CD`) -> BigQuery **Row Access Policy**.

</div>
</div>

---

# 4. Orchestration : Du Task Graph Snowflake au DAG Dataform

Snowflake enferme l'orchestration dans du DDL impératif (`AFTER`, `WAREHOUSE`, sans tests natifs). Antigravity traduit les **7 Tasks + 1 Dynamic Table + 1 Stored Proc** en un DAG **Dataform (`.sqlx`)** versionné dans Git.

<svg viewBox="0 0 1100 315" width="100%" height="290" xmlns="http://www.w3.org/2000/svg" style="font-family: Inter, Arial, sans-serif;">
  <!-- Tier 0 -->
  <rect x="10" y="110" width="205" height="82" rx="10" fill="#e8f0fe" stroke="#1a73e8" stroke-width="2"/>
  <text x="112" y="138" text-anchor="middle" font-size="12.5" font-weight="700" fill="#174ea6">Tier 0 — Root Trigger</text>
  <text x="112" y="159" text-anchor="middle" font-size="11.5" fill="#202124">TSK_00_ROOT_CDC_ROUTER</text>
  <text x="112" y="178" text-anchor="middle" font-size="10.5" fill="#5f6368">CRON 15 min -> Workflow Config</text>

  <!-- Tier 1 -->
  <rect x="265" y="12" width="245" height="78" rx="10" fill="#ffffff" stroke="#1a73e8" stroke-width="1.5"/>
  <text x="387" y="36" text-anchor="middle" font-size="12" font-weight="700" fill="#174ea6">TSK_01A_STAGE_ORDERS</text>
  <text x="387" y="55" text-anchor="middle" font-size="11" fill="#3c4043">Pré-agrégation GMV paniers</text>
  <text x="387" y="73" text-anchor="middle" font-size="10.5" fill="#137333">-> stg_order_baskets.sqlx</text>

  <rect x="265" y="112" width="245" height="78" rx="10" fill="#ffffff" stroke="#1a73e8" stroke-width="1.5"/>
  <text x="387" y="136" text-anchor="middle" font-size="12" font-weight="700" fill="#174ea6">TSK_01B_PARSE_PINGS</text>
  <text x="387" y="155" text-anchor="middle" font-size="11" fill="#3c4043">JSON IoT (exclut 3.8.0-beta)</text>
  <text x="387" y="173" text-anchor="middle" font-size="10.5" fill="#137333">-> stg_clean_delivery_pings.sqlx</text>

  <rect x="265" y="212" width="245" height="78" rx="10" fill="#ffffff" stroke="#1a73e8" stroke-width="1.5"/>
  <text x="387" y="236" text-anchor="middle" font-size="12" font-weight="700" fill="#174ea6">TSK_01C_STAGE_DISPUTES</text>
  <text x="387" y="255" text-anchor="middle" font-size="11" fill="#3c4043">Anti-fanout + jointure 'CBK-'</text>
  <text x="387" y="273" text-anchor="middle" font-size="10.5" fill="#137333">-> stg_order_disputes_agg.sqlx</text>

  <!-- Tier 2 -->
  <rect x="565" y="45" width="250" height="92" rx="10" fill="#e6f4ea" stroke="#137333" stroke-width="2"/>
  <text x="690" y="70" text-anchor="middle" font-size="12" font-weight="700" fill="#137333">TSK_02A_MART_NET_REVENUE</text>
  <text x="690" y="90" text-anchor="middle" font-size="11" fill="#202124">Fan-in (1A + 1C) + SCD2 Commissions</text>
  <text x="690" y="110" text-anchor="middle" font-size="10.5" fill="#137333">-> fct_platform_net_revenue.sqlx</text>
  <text x="690" y="126" text-anchor="middle" font-size="10" fill="#5f6368">+ assertions uniqueKey / nonNull</text>

  <rect x="565" y="168" width="250" height="92" rx="10" fill="#e6f4ea" stroke="#137333" stroke-width="2"/>
  <text x="690" y="193" text-anchor="middle" font-size="12" font-weight="700" fill="#137333">TSK_02B_MART_PRIME_PARTNERS</text>
  <text x="690" y="213" text-anchor="middle" font-size="11" fill="#202124">Fan-in (1A+1B+1C) + 4 règles Prime</text>
  <text x="690" y="233" text-anchor="middle" font-size="10.5" fill="#137333">-> dim_prime_partner_scorecard.sqlx</text>
  <text x="690" y="249" text-anchor="middle" font-size="10" fill="#5f6368">+ DT_LIVE_ZONE_SUPPLY_DEFICIT</text>

  <!-- Tier 3 -->
  <rect x="865" y="102" width="225" height="98" rx="10" fill="#fef7e0" stroke="#f29900" stroke-width="2"/>
  <text x="977" y="128" text-anchor="middle" font-size="12" font-weight="700" fill="#b06000">TSK_03_REFRESH_PBI_AUDIT</text>
  <text x="977" y="149" text-anchor="middle" font-size="11" fill="#202124">Synthèse Power BI +</text>
  <text x="977" y="167" text-anchor="middle" font-size="11" fill="#202124">SP_AUDIT_DISPUTE_CHARGEBACKS</text>
  <text x="977" y="187" text-anchor="middle" font-size="10.5" fill="#137333">-> rpt_pbi + operations/audit.sqlx</text>

  <!-- Edges -->
  <line x1="215" y1="151" x2="263" y2="51" stroke="#5f6368" stroke-width="1.8"/>
  <line x1="215" y1="151" x2="263" y2="151" stroke="#5f6368" stroke-width="1.8"/>
  <line x1="215" y1="151" x2="263" y2="251" stroke="#5f6368" stroke-width="1.8"/>

  <line x1="510" y1="51" x2="563" y2="85" stroke="#137333" stroke-width="1.8"/>
  <line x1="510" y1="251" x2="563" y2="100" stroke="#137333" stroke-width="1.8"/>
  <line x1="510" y1="51" x2="563" y2="195" stroke="#137333" stroke-width="1.8"/>
  <line x1="510" y1="151" x2="563" y2="212" stroke="#137333" stroke-width="1.8"/>
  <line x1="510" y1="251" x2="563" y2="232" stroke="#137333" stroke-width="1.8"/>

  <line x1="815" y1="91" x2="863" y2="140" stroke="#f29900" stroke-width="2"/>
  <line x1="815" y1="214" x2="863" y2="162" stroke="#f29900" stroke-width="2"/>
</svg>

- **Compléments Compute & IA** : le scoring fraude **Snowpark Python** passe sur **Managed Spark (Dataproc Serverless)** ; **Cortex SQL & `ML.FORECAST`** passent sur **BigQuery AI** (`AI.CLASSIFY`, `AI.SCORE`, `AI.FORECAST` avec **TimesFM** zero-shot).

---

# 5. Remplacer Snowflake sans Disruption : Les 3 Bascules Clés

<div class="cols-3">
<div class="card-blue">

### 1. Bascule Airbyte (Amont)
- Connexion Legacy (`Snowflake`) passée en `inactive`.
- Connexion Cible (`BigQuery`) activée sur les mêmes streams (`dlv_ord_hdr`, `dlv_ord_item_ln`, `dsp_refund_fct`) avec préfixe `CDC_` et curseur `updated_at`.
- **Preuve live** : injection de **+50 commandes du 1er avril 2026** dans Postgres -> arrivée immédiate dans BigQuery.

</div>
<div class="card-green">

### 2. Montage Zero-Copy (Données)
- Les 4 tables **Iceberg sur GCS** (70,6 % des lignes) sont montées via `EXTERNAL TABLE ... format = 'ICEBERG'` en **< 5 secondes**, sans recopier les données.
- Les 8 tables **FDN / `VARIANT`** sont exportées en Parquet / JSON GZIP puis chargées en **BigQuery natif** (`JSON`, partitionné et clusterisé).

</div>
<div class="card-yellow">

### 3. Rebranchement Power BI (Aval)
- Projet moderne `.pbip` + `.tmdl` versionné dans Git.
- Antigravity remplace uniquement la partition M-Query :
  `Snowflake.Databases(...)`
  -> `GoogleBigQuery.Database([UseStorageApi=true])`
- **Contrat de schéma conservé** (noms & colonnes MAJUSCULES) -> **0 mesure DAX et 0 visuel cassé**.

</div>
</div>

---

# 6. Sacraliser les KPIs : L'Approche "Knowledge-as-Code"

> **Problème classique** : après une migration, le CFO voit un chiffre dans Power BI, l'analyste SQL en trouve un autre, et l'assistant IA hallucine en tombant dans un piège de jointure.

<div class="cols-2">
<div>

### Extraction Multi-Sources par Antigravity
Antigravity lit **toute la codebase legacy** pour extraire chaque règle métier :
1. **Snowflake SQL** (`03_streams_tasks...`, `04_legacy_views...`) : formules SCD2, filtres de statuts, anti-fanout.
2. **Snowpark Python** (`snowpark_merchant_fraud_scoring.py`) : seuils de risque fraude.
3. **Cortex YAML** (`cortex_ops_model.yaml`) : synonymes & dimensions métier.
4. **Power BI `.tmdl`** : les **11 mesures DAX** exécutives (`Effective Take-Rate %`, `Prime GMV Share %`, etc.).

</div>
<div class="card-green">

### Publication vers Knowledge Catalog
1. **Open Knowledge Format (`OKF v0.2`)** : génération structurée dans `okf/` et `bundle/` (versionnée Git, relisible par les équipes métier).
2. **Métadonnées BigQuery** : injection automatique des descriptions de tables & colonnes.
3. **Knowledge Catalog** :
   - **Business Glossary** & **Context Set** gouvernés.
   - **Usage-Based Data Insights** alimenté par le `QUERY_HISTORY` réel des analystes.
4. **BigQuery Conversational Analytics** : questions ad-hoc en langage naturel **100 % alignées sur Power BI**.

</div>
</div>

---

# 7. Les KPIs Sacralisés & Vérités Terrain (`ground_truth_manifest.json`)

Chaque KPI critique est figé dans un contrat de test automatisé (`evals/verify_migration_parity.py`) qui exige une **parité exacte au centime** avant validation de la bascule.

| KPI Officiel UrbanFork | Formule / Règle Sacralisée | Vérité Terrain (`seed = 42`) | Source Principale |
| :--- | :--- | :--- | :--- |
| **Platform Net Revenue** *(Q3 2025 Restaurants)* | Commission SCD2 + Frais livraison/service − Paie coursier − Promos − Remboursements approuvés *(hors pourboires !)* | **153 150,49 USD** | `FCT_PLATFORM_NET_REVENUE` |
| **FY25 Net Revenue** *(Exercice fiscal : 1er fév.)* | Somme sur `FISC_YR_N = 2025` séparée par vertical (`VERT_CD = 1` Resto vs `2` Grocery) | **937 401,38 USD** *(Resto)*<br>**38 309,66 USD** *(Grocery)* | `FCT_PLATFORM_NET_REVENUE` |
| **Approved Refunds** *(Anti-Fanout)* | Somme dédupliquée au grain commande (`RFND_STS_FLG = 1` uniquement) | **248 632,85 USD** | `DSP_REFUND_FCT` |
| **Prime Partner Scorecard** | 4 seuils cumulatifs sur 90j : GMV > 25k USD, Prep < 14 min, Litiges qualité < 2 %, Rejets < 1 % | Parité stricte `SF == BQ` | `DIM_PRIME_PARTNER_SCORECARD` |
| **Live Supply Deficit Ratio** | `UNASSIGNED_ORD_N / NULLIF(ONLINE_CRR_N - BUSY_CRR_N, 0)` au **dernier snapshot** uniquement | **LON-01 : 5.50**<br>**NYC-01 : 4.50 • PAR-01 : 3.25** | `DT_LIVE_ZONE_SUPPLY_DEFICIT` |

---

# 8. Les Données Générées : Vue d'Ensemble (624 924 lignes)

Un générateur Python déterministe (`data-generator/generate_urbanfork_data.py`, **`seed = 42`**) produit un écosystème réaliste et reproductible couvrant **3 ans d'historique** jusqu'au **`2026-03-31`** (+50 commandes live du `2026-04-01` côté PostgreSQL OLTP).

<div class="cols-3">
<div class="card-blue">
  <div class="kpi-num">441 264</div>
  <strong>Lignes Apache Iceberg (70,6 %)</strong>
  <p class="small">4 tables volumineuses stockées sur GCS en format ouvert Iceberg -> montage <em>Zero-Copy</em> BigLake.</p>
</div>
<div class="card-yellow">
  <div class="kpi-num" style="color:#b06000;">41 375</div>
  <strong>Lignes Native FDN (6,6 %)</strong>
  <p class="small">7 tables relationnelles Snowflake (référentiels, SCD2, litiges) avec Masking PII et Row Access Policy.</p>
</div>
<div class="card" style="background:#f3e8fd; border-left: 5px solid #7627bb;">
  <div class="kpi-num" style="color:#7627bb;">142 285</div>
  <strong>Lignes IoT VARIANT (22,8 %)</strong>
  <p class="small">1 table de télémétrie mobile JSON semi-structurée (Snowpipe) -> BigQuery natif <code>JSON</code>.</p>
</div>
</div>

<br>

- **Empreinte métier réaliste** : **12 villes mondiales / 36 zones** (`EMEA`, `NA`, `APAC`), **400 partenaires** (300 restaurants, 100 dark-stores), **30 000 clients**, **2 500 coursiers**, **90 000 commandes**, **277 146 lignes d'articles**.
- **Année fiscale décalée** : `SYS_CAL_DIM` fait démarrer l'exercice fiscal au **1er février** (piège classique de reporting financier).

---

# 9. Catalogue Détaillé des 12 Tables Sources

| # | Table Snowflake (`URBANFORK_PROD`) | Stockage | Lignes | Rôle & Spécificité Technique | Cible BigQuery |
| :-: | :--- | :--- | --: | :--- | :--- |
| 1 | `OPS_RAW.DLV_ORD_HDR` | <span class="badge b-ice">Iceberg</span> | 90 000 | En-têtes commandes + `STREAM` CDC | BigLake Iceberg + Airbyte `CDC_` |
| 2 | `OPS_RAW.DLV_ORD_ITEM_LN` | <span class="badge b-ice">Iceberg</span> | 277 146 | Lignes paniers (calcul GMV) | BigLake Iceberg + Airbyte `CDC_` |
| 3 | `OPS_RAW.ZNE_FLEET_SNAP` | <span class="badge b-ice">Iceberg</span> | 60 372 | Snapshots flotte toutes les 15 min | BigLake Iceberg (`DT_LIVE...`) |
| 4 | `OPS_RAW.MRC_PAYOUT_LEDGER` | <span class="badge b-ice">Iceberg</span> | 13 746 | Grand livre paiements & chargebacks | BigLake Iceberg |
| 5 | `IOT_RAW.APP_DELIVERY_PINGS` | <span class="badge b-iot">VARIANT</span> | 142 285 | Pings GPS JSON + `SNOWPIPE` | BigQuery Native **`JSON`** |
| 6 | `OPS_RAW.CUST_USER_MSTR` | <span class="badge b-fdn">FDN</span> | 30 000 | Clients + **Masking PII** (`EMAIL`, `PHONE`) | Native + **Policy Tags (CLS)** |
| 7 | `OPS_RAW.CRR_COURIER_MSTR` | <span class="badge b-fdn">FDN</span> | 2 500 | Coursiers + **Masking PII** (`PHONE`) | Native + **Policy Tags (CLS)** |
| 8 | `OPS_RAW.GEO_ZONE_LKP` | <span class="badge b-fdn">FDN</span> | 36 | Zones géo + **Row Access Policy (`REG_CD`)** | Native + **BigQuery RLS** |
| 9 | `OPS_RAW.MRC_PARTNER_MSTR` | <span class="badge b-fdn">FDN</span> | 400 | Catalogue 400 marchands | Native (`CLUSTER BY ZONE_ID`) |
| 10 | `OPS_RAW.MRC_COMM_SCD2` | <span class="badge b-fdn">FDN</span> | 1 100 | Historique SCD2 des commissions | Native (`PARTITION BY EFF_FROM_DT`) |
| 11 | `OPS_RAW.DSP_REFUND_FCT` | <span class="badge b-fdn">FDN</span> | 6 243 | Litiges, tickets texte (Cortex/BQ AI) | Native + Airbyte + **`AI.CLASSIFY`** |
| 12 | `OPS_RAW.SYS_CAL_DIM` | <span class="badge b-fdn">FDN</span> | 1 096 | Calendrier fiscal (début 1er février) | Native |

---

# 10. Les 5 Pièges Analytiques Injectés dans les Données

Pour démontrer la valeur réelle de **Dataform**, **OKF v0.2** et **Knowledge Catalog**, 5 pièges classiques d'entreprise sont volontairement plantés dans les données :

| Piège Injecté | Erreur d'une requête naïve / IA sans contexte | Chiffre Faux | Vérité Terrain | Écart / Impact |
| :--- | :--- | --: | --: | :--- |
| **#1 SCD2 Commissions** (`MRC_COMM_SCD2`) | Joindre sur `IS_CURR_FLG = 1` au lieu de `ORD_DT BETWEEN EFF_FROM_DT AND EFF_TO_DT` | **280 447,29 USD** | **153 150,49 USD** | **+127 296,80 USD** *(+83 % d'erreur sur Q3 !)* |
| **#2 Fan-Out Remboursements** (`DSP_REFUND_FCT`) | Joindre `DSP_REFUND_FCT` directement avec `DLV_ORD_ITEM_LN` sans pré-agrégation | **813 512,14 USD** | **248 632,85 USD** | **×3,27** *(surévaluation massive)* |
| **#3 Snapshot Trap** (`ZNE_FLEET_SNAP`) | Faire `SUM(ONLINE_CRR_N)` sur plusieurs timestamps au lieu du dernier snapshot | **76 734 coursiers** *(Londres)* | **95 coursiers** *(Londres)* | **×807** *(mesure non-additive !)* |
| **#4 Jointure Cachée** (`MRC_PAYOUT_LEDGER`) | Chercher une clé étrangère `ORD_ID` alors que la clé est `'CBK-' \|\| ORD_ID` dans `REF_DOC_TXT` | **0 USD** de chargebacks | Chargebacks réconciliés | Règle capturée dans **OKF** & **Usage Joins** |
| **#5 Bug JSON & Fraudeurs** (`APP_DELIVERY_PINGS`) | Oublier d'exclure `app_ver = '3.8.0-beta'` (`1 933` commandes au timer GPS faux) + `45` fraudeurs sériels | SLA cuisine faussés | SLA exacts + 45 fraudeurs détectés | Filtré dans **Dataform** + scoré dans **Spark** |

---

# 11. Déroulé de la Démonstration Live (45 Minutes)

| Temps | Acte | Action orchestrée par Antigravity | Preuve visible à l'écran |
| :--- | :--- | :--- | :--- |
| **00–05 min** | **Acte 1 : Audit Live** | Inspection complète de Snowflake (`URBANFORK_PROD`), Airbyte, 7 Tasks et Power BI `.tmdl`. | Blueprint `MIGRATION_AUDIT_REPORT.md` + Snowsight Task Graph. |
| **05–13 min** | **Acte 2 : Données & Airbyte** | Montage **Zero-Copy BigLake** (4 Iceberg) + chargement 8 FDN/`JSON` + bascule **Airbyte -> BigQuery** + 50 commandes live. | `624 924` lignes migrées + 50 commandes du 1er avril atterrissent dans BigQuery via Airbyte UI. |
| **13–26 min** | **Acte 3 : Dataform, Spark & AI** | Conversion du 7-Node Task Graph en **DAG Dataform** + **Managed Spark** + **BigQuery AI** (`AI.CLASSIFY`, TimesFM `AI.FORECAST`). | Graphe compilé Dataform vs Snowsight + **`153 150,49 == 153 150,49`** dans `verify_migration_parity.py`. |
| **26–37 min** | **Acte 4 : KPIs -> OKF & KC** | Extraction des règles SQL + Python + DAX -> **OKF v0.2** -> métadonnées BigQuery, **Knowledge Catalog** & `QUERY_HISTORY`. | Schémas BigQuery documentés + onglet **Insights** (jointures d'usage) + Glossary / Context Set. |
| **37–45 min** | **Acte 5 : Power BI & Q&A IA** | Refactoring des `.tmdl` vers `GoogleBigQuery.Database()` + questions executives dans **BigQuery Conversational Analytics**. | Power BI rafraîchi sans casse + Q&A IA évitant les 5 pièges analytiques ! |

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Synthèse : Pourquoi cette Migration Change la Donne

<br>

1. **Zéro disruption opérationnelle** : Airbyte garde ses curseurs, BigLake lit Iceberg *Zero-Copy*, Power BI garde 100 % de ses visuels.
2. **Modernisation immédiate** : fin des Tasks impératives et warehouses à dimensionner -> **Dataform + BigQuery Serverless + BigQuery AI**.
3. **KPIs sacralisés & gouvernés** : la connaissance métier est extraite une fois pour toutes en **OKF v0.2 / Knowledge Catalog** — garantissant un chiffre unique au centime entre BI et IA conversationnelle.
