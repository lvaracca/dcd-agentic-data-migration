# Brief Démo & Slides — Migration Snowflake vers Google Cloud (QuickBite)

> **Objectif** : Document de pilotage pour finaliser le **recording de la démo avant jeudi** et fournir à **Johan** tous les éléments prêts à intégrer dans le pitch (message clé ultra-concis, diagramme Mermaid et déroulé des séquences).

---

## PARTIE 1 — Kit Prêt-à-Intégrer pour Johan (Slides du Pitch)

### 1.1 Ce que la démo prouve (Version ultra-concise pour les slides)

**Thèse centrale** : *Migrer de Snowflake vers Google Cloud avec **Antigravity** ne se limite pas à copier des tables — on remplace tout le cœur analytique **sans disruption** (de l'ingestion Airbyte jusqu'à **Tableau Cloud**) tout en **sacralisant les KPIs métier** pour l'IA.*

- **1. Zéro disruption de bout en bout** :
  - **En amont** : Airbyte bascule de Snowflake vers BigQuery en gardant ses curseurs incrémentaux — aucune commande live perdue.
  - **Sur les données** : les tables **Apache Iceberg** sur GCS sont montées en **Zero-Copy** dans BigQuery (**BigLake**) en quelques secondes.
  - **En aval** : **Tableau Cloud** est rebranché en direct de Snowflake vers BigQuery (*Replace Data Source*) sans casser un seul *Calculated Field* ni un seul graphique (et le même contrat de schéma s'applique à Power BI).
- **2. Modernisation complète Orchestration, Spark & IA** :
  - Un DAG complexe de **7 Snowflake Tasks** + Dynamic Table + Stored Proc est converti automatiquement en **Dataform** (Git + tests intégrés), Snowpark en **Managed Spark**, et Cortex en **BigQuery AI** (`AI.CLASSIFY`, `AI.FORECAST` TimesFM).
- **3. Sacralisation des KPIs & Parité au centime (Knowledge-as-Code)** :
  - Toute la logique métier cachée (SQL Snowflake, Snowpark Python, règles BI) est extraite vers **GitHub / Open Knowledge Format (OKF)** et **Google Cloud Knowledge Catalog**.
  - **Preuve chiffrée** : parité mathématique exacte au centime (**\$153 150,49** de Net Revenue Q3 Restaurants), et **BigQuery Conversational Analytics** déjoue automatiquement les 5 pièges analytiques (SCD2 commissions, fan-out remboursements, snapshot trap flotte, jointure chargeback cachée, bug GPS JSON).

---

### 1.2 Diagramme d'Architecture (Mermaid)

*(Copiable tel quel sur [mermaid.live](https://mermaid.live) pour export SVG/PNG haute définition dans les slides.)*

```mermaid
flowchart LR
    subgraph UP["1. Ingestion Amont (VM Privée GCE)"]
        PG["PostgreSQL OLTP<br/>(Commandes Live)"]
        AB["Airbyte OSS<br/>(Sync Incrémental CDC)"]
        PG --> AB
    end

    subgraph LEGACY["AVANT : Legacy Snowflake (QUICKBITE_PROD)"]
        SF_RAW["Stockage Hybride<br/>4 Tables Iceberg (GCS)<br/>+ 8 Natives / VARIANT JSON"]
        SF_ORCH["Orchestration & Compute<br/>7-Node Task DAG + Streams<br/>Dynamic Table + Snowpark + Cortex"]
        SF_MART["Gold Marts<br/>(Revenus, Prime Partners, Flotte)"]
        SF_RAW --> SF_ORCH --> SF_MART
    end

    subgraph GCP["APRÈS : Google Cloud (dcd-migration-demo • us-central1)"]
        BQ_RAW["BigQuery Raw Layer<br/>Zero-Copy BigLake Iceberg<br/>+ Native JSON + Policy Tags / RLS"]
        BQ_ORCH["Dataform DAG (.sqlx + Tests)<br/>+ Managed Spark (Dataproc)<br/>+ BigQuery AI (Gemini / TimesFM)"]
        BQ_MART["BigQuery Gold Marts<br/>Contrat de schéma 100 % identique<br/>Parité vérifiée au centime"]
        KC["Knowledge Catalog & OKF v0.2<br/>Règles extraites de SQL + Python + DAX<br/>Glossary • Context Set • Usage Joins"]
        BQ_RAW --> BQ_ORCH --> BQ_MART
        BQ_RAW & BQ_MART --> KC
    end

    subgraph DOWN["2. Consommation Aval (BI & IA)"]
        BI["Tableau Cloud Executive Cockpit<br/>(Replace Data Source • 0 KPI cassé)"]
        CA["BigQuery Conversational Analytics<br/>(Q&A Métier Fiabilisé)"]
    end

    AB -. "Avant : Snowflake" .-> SF_RAW
    AB == "Bascule Live : BigQuery (ADC)" ==> BQ_RAW
    SF_MART -. "Avant : Connecteur Snowflake" .-> BI
    BQ_MART == "Rebranchement : Connecteur BigQuery" ==> BI
    KC & BQ_MART ==> CA

    style LEGACY fill:#fce8e6,stroke:#c5221f,stroke-dasharray: 5 5
    style GCP fill:#e6f4ea,stroke:#137333,stroke-width:2px
    style KC fill:#fef7e0,stroke:#f29900,stroke-width:1.5px
    style UP fill:#e8f0fe,stroke:#1a73e8
    style DOWN fill:#f8f9fa,stroke:#5f6368
```

---

### 1.3 Storyboard des 5 Clips Muets (~4 min au total — 1 Clip par Slide)

> **Format recommandé pour le pitch de jeudi** : **5 clips muets courts (`30 s` à `60 s` max)** insérés chacun sur sa propre slide (zéro temps d'attente/spinner, pause nette de 3 secondes sur chaque preuve visuelle). Le présentateur commente en live à son rythme puis clique pour passer au clip suivant.

| Clip / Slide | Titre Slide | Durée max | Plans visuels exacts (vidéo muette) | Verbatim clé à dire en live (2 phrases) |
| :--- | :--- | :-: | :--- | :--- |
| **Clip 1** | **Existant & Audit IA** | `30 s` | Snowsight (*Task Graph* 7 nœuds) -> Airbyte UI (`Snowflake` actif en vert) -> scroll rapide sur `MIGRATION_AUDIT_REPORT.md`. | *« Une migration Snowflake ne se résume jamais à déplacer des tables : tout un écosystème vit autour, d'Airbyte jusqu'à Power BI. Antigravity audite automatiquement toute la chaîne avant de toucher à la production. »* |
| **Clip 2** | **Données Hybrides & Bascule Airbyte** | `45 s` | BigQuery `quickbite_raw_ops` (`*_ICEBERG_EXT` *Zero-Copy* + `APP_DELIVERY_PINGS` en `JSON` natif) -> Airbyte UI (`BigQuery` actif, ADC sans clé) -> requête `SELECT COUNT(*) FROM CDC_dlv_ord_hdr` (`51` commandes live). | *« Les tables Apache Iceberg sur GCS sont montées en Zero-Copy grâce à BigLake, sans recopie réseau. En parallèle, Airbyte bascule à chaud sur BigQuery sans perdre une seule commande live. »* |
| **Clip 3** | **7 Tasks -> Dataform, Parité & BQ AI** | `60 s` | **Dataform Compiled Graph** (`quickbite-lakehouse-dag`, 11 assertions vertes) -> terminal `verify_migration_parity.py` (pause 3 s sur **`\$153,150.49 == \$153,150.49`**) -> aperçu `FCT_REGIONAL_ORDER_FORECAST_14D` (**TimesFM 2.5**) & `BQ_AI_DISPUTE_TRIAGE`. | *« L'orchestrateur Snowflake est transformé en un DAG Dataform versionné avec tests de qualité intégrés et parité prouvée au centime près. On modernise au passage Snowpark et Cortex vers Spark et BigQuery AI (Gemini & TimesFM) directement en SQL. »* |
| **Clip 4** | **Sacraliser les KPIs (GitHub & Knowledge Catalog)** | `45 s` | Dossier `bundle/` sur **GitHub (`dcd-agentic-data-migration`)** -> BigQuery Studio **Schema** de `FCT_PLATFORM_NET_REVENUE` (colonnes enrichies) + onglet **Insights** / Context Set Knowledge Catalog. | *« Une migration, c'est aussi en profiter pour formaliser et centraliser les KPIs métier une fois pour toutes. Antigravity extrait les règles cachées du SQL, de Python et du DAX vers GitHub et Knowledge Catalog. »* |
| **Clip 5** | **Tableau Cloud Intact & Conversational Analytics** | `60 s` | **Tableau Cloud** connecté à Snowflake (`\$153,150.49`) -> **Replace Data Source -> BigQuery** (0 KPI cassé, chiffres identiques) -> 2 questions/réponses dans **Conversational Analytics** (pause 3 s sur **`\$153 150,49`** et Top 3 zones **`5.50 / 4.50 / 3.25`**). | *« Côté Tableau Cloud, on débranche Snowflake et on branche BigQuery en 3 clics sans casser un seul KPI ni un seul graphique. Et grâce aux KPIs sacralisés, l'IA conversationnelle répond exactement le même chiffre au centime, en déjouant tous les pièges analytiques. »* |

---

## PARTIE 2 — Pilotage Technique jusqu'à Jeudi (Fait vs. Reste à Faire)

### 2.1 Ce qui est DÉJÀ fait et vérifié en live (Dry Run 100 % validé ✅)

| Composant | Statut | Détail vérifié |
| :--- | :---: | :--- |
| **Données synthétiques déterministes** | ✅ Fait | `624 924` lignes (`seed = 42`) + `ground_truth_manifest.json` avec les 5 pièges analytiques. |
| **Snowflake Enterprise Trial (`QUICKBITE_PROD`)** | ✅ Fait | 4 tables Iceberg sur GCS + 8 FDN/`VARIANT`, 7-Node Task DAG + Dynamic Table + Stored Proc + Snowpark + ML.FORECAST + Masking/RLS + `QUERY_HISTORY`. Warehouses suspendus (`AUTO_SUSPEND = 60`). |
| **Acte 1 — Audit Live** | ✅ Validé | `inspect_snowflake_estate.py` exécuté (`11 s`) -> `gcp-target/MIGRATION_AUDIT_REPORT.md`. |
| **Acte 2 — Données Hybrides & Airbyte Live** | ✅ Validé | 4 Iceberg Zero-Copy BigLake + 8 FDN/`JSON` natif + RLS `GEO_ZONE_LKP` + bascule Airbyte (`quickbite-airbyte-vm`) vers BigQuery (ADC keyless) + 51 lignes synchronisées dans `CDC_dlv_ord_hdr`. |
| **Acte 3 — Dataform, Spark & BigQuery AI** | ✅ Validé | Repo Dataform live `quickbite-lakehouse-dag` (`dev-antigravity`, 32 actions, 11 assertions `SUCCEEDED`), **parité 100 % au centime** (`\$153 150,49 == \$153 150,49`), PySpark vectorisé, `AI.CLASSIFY`/`AI.SCORE` et `TimesFM 2.5` exécutés en live. |
| **Acte 4 — OKF v0.2 & Métadonnées BigQuery** | ✅ Validé | `bundle/` & `okf/` générés, 11 tables / 63 colonnes documentées dans BigQuery + `QUERY_HISTORY` alimenté. |
| **Acte 5 — Power BI (`.pbip` / `.tmdl`)** | ✅ Validé | 3 tables Gold rebranchées sur `GoogleBigQuery.Database([UseStorageApi=true])` -> `validate_tmdl_cutover.py` **PASSED (0 mesure DAX cassée)**. |
| **Dépôt GitHub + Script de Reset** | ✅ Fait | Dépôt privé poussé : https://github.com/lvaracca/dcd-agentic-data-migration + `scripts/reset_demo_to_before.sh`. |

---

### 2.2 Ce qu'il RESTE à faire avant jeudi

1. **Publier le Context Set dans Knowledge Catalog** *(optionnel / bonus visuel pour le Clip 4)* :
   - Installer une version officiellement signée de Node.js LTS sur Mac (ou passer par **Google Cloud Shell**) puis `@google-cloud/kcmd`, convertir `bundle/` au format recommandé et publier le Context Set dans `dcd-migration-demo` (`us-central1`).
2. **Tourner les 5 clips muets (`30–60 s`, `1920×1080`, zoom Chrome `125 %`, terminal `18 pt`)** :
   - Les Clips 2, 3, 4 et 5 peuvent être filmés **dès maintenant** (tout est déjà déployé et chaud dans BigQuery Studio / Dataform / Airbyte).
   - Utiliser `scripts/reset_demo_to_before.sh` uniquement si vous souhaitez filmer l'état « BigQuery vide / Airbyte connecté à Snowflake » pour le début du Clip 1.
3. **Transmettre à Johan** : la **Partie 1** de ce document (message clé + diagramme Mermaid + storyboard des 5 clips) + les 5 fichiers vidéo `.mp4`.

---

## PARTIE 3 — Flow Complet & Commandes Exactes de la Démo

### Pré-vol (2 minutes avant de lancer l'enregistrement)
```bash
# 1. Ouvrir l'UI Airbyte sur http://localhost:8000 (dans un terminal dédié)
./scripts/open_airbyte_ui_tunnel.sh

# 2. Ouvrir 3 onglets Chrome côte à côte :
#    - Onglet 1 : Snowsight (https://app.snowflake.com/zsemzzy/il11049) -> QUICKBITE_PROD + Task Graph
#    - Onglet 2 : Airbyte UI (http://localhost:8000) -> Connexion Snowflake active en vert
#    - Onglet 3 : Google Cloud Console -> BigQuery Studio (dcd-migration-demo, us-central1)
```

### Flow pas-à-pas (Prompts Antigravity & Scripts sous-jacents)

| Étape | Prompt Antigravity (ou commande manuelle) | Script exécuté sous le capot | Résultat attendu à filmer |
| :--- | :--- | :--- | :--- |
| **Acte 1** *(Audit)* | *"Audit our live Snowflake QUICKBITE_PROD environment, upstream Airbyte Terraform pipeline, 7-node Snowflake Task DAG, and downstream Power BI (.pbip / TMDL) model. Generate the GCP migration blueprint in gcp-target/MIGRATION_AUDIT_REPORT.md."* | `.venv/bin/python .agents/skills/snowflake-live-audit/scripts/inspect_snowflake_estate.py` | Génération de `gcp-target/MIGRATION_AUDIT_REPORT.md` listant les 12 tables, 7 Tasks, politiques & 11 mesures DAX. |
| **Acte 2** *(Données + Airbyte)* | *"Execute the hybrid Snowflake-to-BigQuery data migration (Zero-Copy BigLake Iceberg for our 4 GCS Iceberg tables + Parquet/native JSON load for the 8 FDN/VARIANT tables), start background Data Profile scans, and re-point our Airbyte pipeline seamlessly from Snowflake to BigQuery."* | 1. `.venv/bin/python .agents/skills/snowflake-hybrid-data-cutover/scripts/migrate_hybrid_tables_to_bq.py`<br>2. `.venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action cutover-to-bigquery`<br>3. `.venv/bin/python ingestion-airbyte/simulate_live_orders.py --count 50`<br>4. `.venv/bin/python ingestion-airbyte/airbyte_cutover_controller.py --action trigger-sync` | 12 tables peuplées dans BigQuery (`624 924` lignes) + bascule visible dans l'UI Airbyte + 50 nouvelles commandes (`2026-04-01`) dans `quickbite_raw_ops.CDC_dlv_ord_hdr`. |
| **Acte 3A** *(Tasks -> Dataform)* | *"Migrate our 7-node Snowflake Task Graph, Dynamic Table, Views, and Stored Procedure into a BigQuery Dataform repository under gcp-target/dataform/ (preserving exact uppercase Power BI schema contracts), compile and execute the Dataform DAG, and run evals/verify_migration_parity.py."* | 1. Compilation & exécution Dataform (`gcp-target/dataform/`)<br>2. `.venv/bin/python evals/verify_migration_parity.py --compare-live-snowflake` | Graphe compilé Dataform dans BigQuery Studio + console verte **`$153,150.49 == $153,150.49`** & **`$248,632.85 == $248,632.85`**. |
| **Acte 3B** *(Spark & BQ AI)* | *"Migrate our Snowpark fraud-scoring Python job to Google Cloud Managed Spark under gcp-target/spark/ and convert our Snowflake Cortex SQL & ML Forecast scripts to zero-shot BigQuery AI (AI.CLASSIFY, AI.SCORE, and TimesFM AI.FORECAST) under gcp-target/bigquery-ai/, then execute the BigQuery AI queries."* | `gcp-target/spark/pyspark_fraud_scoring_serverless.py` + `bq query` sur `gcp-target/bigquery-ai/cortex_to_bq_ai.sql` | Prévision 14 jours TimesFM (`FCT_REGIONAL_ORDER_FORECAST_14D`, 42 lignes) + triage IA des tickets clients (`BQ_AI_DISPUTE_TRIAGE`). |
| **Acte 4** *(KPIs -> OKF & KC)* | *"Extract all undocumented business logic, status code definitions, analytical join traps, and KPI formulas from Snowflake SQL, Snowpark Python, cortex_ops_model.yaml, and Power BI .tmdl DAX measures into Open Knowledge Format (okf/ and bundle/). Then push descriptions to BigQuery and seed query history for Knowledge Catalog Data Insights."* | `.venv/bin/python .agents/skills/extract-business-logic-to-okf/scripts/push_okf_metadata_and_seed_history.py` *(+ publication Context Set via `curate-context`)* | Colonnes documentées dans BigQuery Studio + onglet **Insights** montrant les jointures d'usage (`'CBK-'`, SCD2). |
| **Acte 5** *(Power BI & Q&A)* | *"Unplug our Power BI Semantic Model in bi-powerbi/ from Snowflake and re-point all table partitions to BigQuery using GoogleBigQuery.Database with the Storage API, keeping 100% of DAX measures and visuals intact, then validate the cutover."* | `.venv/bin/python .agents/skills/repoint-powerbi-to-bigquery/scripts/validate_tmdl_cutover.py` + prompts dans **BigQuery Conversational Analytics** (`evals/conversational_analytics_test_prompts.md`) | Validation 100 % verte des `.tmdl` + réponses IA exactes (**\$153 150,49** Q3 Restaurants, Top 3 zones déficit **5.50 / 4.50 / 3.25** sans Snapshot Trap). |
