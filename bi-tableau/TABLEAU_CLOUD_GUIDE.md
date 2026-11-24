# QuickBite — Guide Tableau Cloud (Setup en 8 min & Bascule Live Snowflake -> BigQuery)

Ce guide permet de monter un vrai **QuickBite Executive Cockpit** dans **Tableau Cloud** (100 % navigateur Chrome, zéro installation sur Mac) et de filmer la **bascule sans disruption** de **Snowflake** vers **Google BigQuery** pour le **Clip 5**.

---

## Étape 1 — Créer votre essai gratuit Tableau Cloud (2 min)
1. Allez sur https://www.tableau.com/products/cloud-bi (essai gratuit 14 jours, 100 % web).
2. Connectez-vous à votre site Tableau Cloud dans Chrome.

---

## Étape 2 — Connecter la source AVANT : Snowflake (`QUICKBITE_PROD.MART`) (2 min)
1. Cliquez sur **New -> Workbook** -> onglet **Connectors -> Snowflake**.
2. Renseignez les paramètres exacts :
   - **Server** : `zsemzzy-il11049.snowflakecomputing.com`
   - **Role** : `ACCOUNTADMIN`
   - **Authentication** : `Username and Password`
   - **Username** : `LVARACCA`
   - **Password** : votre token PAT Snowflake (`SNOWFLAKE_PASSWORD` dans votre fichier `.env` local)
3. Cliquez sur **Sign In**, puis sélectionnez :
   - **Warehouse** : `QB_TRANSFORM_WH`
   - **Database** : `QUICKBITE_PROD`
   - **Schema** : `MART`
4. Glissez la table **`FCT_PLATFORM_NET_REVENUE`** dans le canevas Data Source.
5. Renommez la source de données en haut : **`QuickBite_Net_Revenue_Snowflake`**.

*(Note : `QB_TRANSFORM_WH` est configuré avec `AUTO_SUSPEND = 60` — il se mettra automatiquement en veille 60 secondes après vos tests.)*

---

## Étape 3 — Créer les 4 KPIs & le Dashboard « QuickBite Executive Cockpit » (4 min)

Créez ces **Calculated Fields** (menu **Analysis -> Create Calculated Field**) — tous utiliseront les noms de colonnes **MAJUSCULES**, 100 % identiques entre Snowflake et BigQuery :

1. **`Effective Take-Rate %`**
   ```text
   SUM([PLATFORM_NET_REVENUE_USD]) / SUM([GROSS_MERCHANDISE_VALUE_USD])
   ```
   *(Format : Pourcentage `0.00%`)*

2. **`Q3 2025 Restaurant Net Revenue ($)`** *(vérifie en direct le benchmark SCD2 = `$153,150.49` !)*
   ```text
   SUM(
     IF [CAL_DT] >= #2025-07-01# AND [CAL_DT] <= #2025-09-30# AND [VERT_CD] = 1
     THEN [PLATFORM_NET_REVENUE_USD]
     ELSE 0
     END
   )
   ```
   *(Format : Currency `$#,##0.00` — doit afficher exactement **`$153,150.49`** !)*

3. **`FY25 Restaurant Net Revenue ($)`** *(benchmark exercice fiscal = `$937,401.38`)*
   ```text
   SUM(
     IF [FISC_YR_N] = 2025 AND [VERT_CD] = 1
     THEN [PLATFORM_NET_REVENUE_USD]
     ELSE 0
     END
   )
   ```

4. **`Approved Refund Ratio %`** *(benchmark anti-fanout = `$248,632.85` sur total approuvé)*
   ```text
   SUM([APPROVED_REFUNDS_USD]) / SUM([GROSS_MERCHANDISE_VALUE_USD])
   ```

### 3 feuilles simples + 1 Dashboard (format `Desktop 16:9` pour la vidéo)
- **Feuille 1 (`KPI Cards`)** : glissez `Q3 2025 Restaurant Net Revenue ($)`, `FY25 Restaurant Net Revenue ($)`, `SUM(APPROVED_REFUNDS_USD)`, `Effective Take-Rate %` en **Text** (gros chiffres en bannière).
- **Feuille 2 (`Monthly Net Revenue by Vertical`)** : `MONTH(CAL_DT)` en Colonnes, `SUM(PLATFORM_NET_REVENUE_USD)` en Lignes, `VERTICAL_NM` en Couleur (courbe ou barres empilées).
- **Feuille 3 (`Regional Performance`)** : `REG_CD` + `CITY_NM` en Lignes, `SUM(PLATFORM_NET_REVENUE_USD)` en Colonnes, `Effective Take-Rate %` en Couleur.
- **Dashboard (`QuickBite Executive Cockpit`)** : assemblez les 3 feuilles (Bannière KPIs en haut, Courbe mensuelle à gauche, Barres régionales à droite) et cliquez sur **Publish As** (`QuickBite_Executive_Cockpit`).

---

## Étape 4 — Ajouter la source APRÈS : Google BigQuery (`quickbite_gold_mart`) (1 min)
1. Dans le même workbook, cliquez sur **Data -> New Data Source -> Google BigQuery**.
2. Connectez-vous en 1 clic via **Google OAuth** (`admin@lvaracca.altostrat.com`).
3. Sélectionnez :
   - **Billing Project** : `dcd-migration-demo`
   - **Project** : `dcd-migration-demo`
   - **Dataset** : `quickbite_gold_mart`
   - **Table** : glissez **`FCT_PLATFORM_NET_REVENUE`**
4. Renommez la source en **`QuickBite_Net_Revenue_BigQuery`**.

---

## Étape 5 — La séquence « Effet Waouh » à filmer pour le Clip 5 (30 secondes !)
1. Ouvrez le dashboard **`QuickBite Executive Cockpit`** connecté à **Snowflake** — montrez les chiffres clés (**`$153,150.49`**, **`$937,401.38`**, **`$248,632.85`**).
2. Allez sur une feuille -> menu **Data -> Replace Data Source...** :
   - **Current** : `QuickBite_Net_Revenue_Snowflake`
   - **Replacement** : `QuickBite_Net_Revenue_BigQuery`
   - Cliquez sur **OK**.
3. Revenez sur le dashboard **`QuickBite Executive Cockpit`** -> faites une **pause nette de 3 secondes** :
   - **0 point d'exclamation rouge (`!`)**, **0 Calculated Field cassé**, **0 graphique à refaire**.
   - **Mêmes chiffres exacts au centime près (`$153,150.49`, `$937,401.38`, `$248,632.85`)**, désormais propulsés à 100 % par **Google BigQuery** !
4. *(Optionnel)* Fermez la source Snowflake (`Close`) pour montrer que Snowflake est officiellement débranché.

> **Bonus automatisation Antigravity** : si vous téléchargez le workbook (`.twb`) depuis Tableau Cloud, vous pouvez aussi exécuter `.venv/bin/python bi-tableau/repoint_twb_to_bigquery.py --input <fichier.twb>` pour montrer le refactoring automatique du XML Tableau (Snowflake -> BigQuery) dans Git !
