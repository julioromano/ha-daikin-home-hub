# Official manuals and compatibility evidence

Reviewed **2026-10-28**. These manufacturer sources establish the interface and provide routes to equipment operating/setup manuals. Unit manuals are supplementary operating references; the HomeHub guide establishes Modbus compatibility and encodings.

## HomeHub sources

| Document | Revision | Source and purpose |
| --- | --- | --- |
| EKRHH installer reference guide | **4P744838-1E, 2026.01** | [Official English PDF](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/accessories/ekrhh/EKRHH_Installer%20reference%20guide_4PEN744838-1E_English.pdf). Compatibility pp. 7-8; Altherma map pp. 39-44; Smart Grid pp. 45-47; air-to-air map/behavior pp. 48-52; configuration pp. 56-62. |
| EKRHH installation manual | **4P702816-1C, 2024.05** | [Official English PDF](https://www.daikin.eu/content/dam/document-library/installation-manuals/heat/air-to-water-heat-pump-mid-temperature/ekrhh/EKRHH_Installation%20manual_4PEN702816-1C_English.pdf). Hardware installation; use the newer reference guide for register behavior. |
| HomeHub product/download index | Web page reviewed 2026-10-28 | [Official product page](https://www.daikin.eu/en_us/products/product.html/EKRHH.html). Source of the current installation/reference-guide downloads. |

The register tables and compatibility footnotes were visually checked. Local source PDFs, checksums and retrieval records belong under ignored `.cache/reference-docs/daikin/`; manufacturer PDFs are not redistributed with the integration.

## Equipment manual index

These are representative official manuals or manufacturer download pages for every supported Altherma profile. Match the actual indoor/outdoor code before using a manual: one listed installation manual does not cover every indoor configuration. Revisions below are those observed in the linked PDF or official download listing, not a claim that every page of each equipment manual has been reviewed.

| Profile | Representative reference and revision | Manufacturer source |
| --- | --- | --- |
| Altherma 3 H HT | EPRA14-18D + ETBH/X16E installer reference, **4P644736-1D** | [Official product downloads](https://www.daikin.eu/en_us/products/product.html/etbh16e9w---epra014-018dv.html); also offers unit operation/user guides. |
| Altherma 3 H MT | EPRA08-12E + ETSH(B)/ETSX(B)12E installer reference, **4P759877-1A** | [Official product downloads](https://www.daikin.eu/en_us/products/product.html/ETSX12E---EPRA08-12EV.html). Select the appropriate indoor configuration. |
| Altherma 3 R ERGA floor/wall | ERGA04-08E + EHBH/X-E installer reference, **4P629085-1, 2020.08** | [Official English PDF](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/EHBH-E6V%2CEHBH-E9W%2CEHBX-E6V%2CEHBX-E9W%2CERGA04-08EV%2CERGA04-08EVA_4PEN629085-1_Installer%20reference%20guide_English.pdf); [official archived product downloads](https://www.daikin.eu/en_us/products/product.html/ehbh-e6v---erga04-08ev.html). HomeHub's newer firmware requirements still apply. |
| Altherma 3 R ERGA ECH₂O | ERGA-E + EHSH/X(B)-E installer reference, **4P759881-1A, 2025.03**; operation manual **4P678718-1D** | [Official product downloads](https://www.daikin.eu/en_us/products/product.html/ehsh-e.html). |
| Altherma 3 R ERLA | ERLA11-16D + EBSH/X(B)-D installer reference, **4P759879-1A, 2025.03** | [Official English PDF](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/erla11-14d/ERLA11-14D%28V3.W1%29.ERLA-D%28V3.W1%297.EBSH%28B%29-D.EBSX%28B%29-D_Installer%20reference%20guide_4PEN759879-1A_English.pdf). |
| Altherma 3 R MT | ERRA08-12E + ELSH/X(B)-E installer reference, **4P759885-1C, 2025.11** | [Official product downloads](https://www.daikin.eu/en_us/products/product.html/ELSH-E---ERRA08-12EV3.html). |
| Altherma 3 M D-series | EBLA/EDLA09-16D installer reference, **4P620241-1B, 2022.05** | [Official English PDF](https://www.daikin.eu/content/dam/document-library/Installer-reference-guide/heat/air-to-water-heat-pump-low-temperature/ebla09-14dv3/EB_DLA09-14D3V3_W1_EB_DLA-D3V3_W1_Installer%20reference%20guide_4PEN620241-1B_English.pdf). |
| Altherma 3 M E-series | EBLA/EDLA04-08E installer reference **4P685228-1B**; operation manual **4P685230-1C**; user reference **4P685231-1A** | [Official product downloads](https://www.daikin.eu/en_us/products/product.html/EBLA04-08E3V3.html). |
| Air-to-air installation | HomeHub guide **4P744838-1E**, pp. 8 and 48-52 | Eligibility is defined by fourth-generation WLAN adapter support **BRP069C4*** and outdoor **Demand Control**, with at most five units. Refer to the actual indoor/outdoor manuals for equipment setup; no exhaustive list of individual air-to-air model codes is asserted. |

## Applicability and boundaries

All eight Altherma profiles use the published use-case-3 register map. Their selectable grouping separates the two documented thermostat exclusions: ERGA floor/wall and M D-series with Micon `20002203`. HomeHub requires unified MMI2 **7.8.0 or newer**. The complete indoor/outdoor combinations remain those in the HomeHub guide's page-7 table, including the F, W and ECH₂O variants.

The guide's Multi+(DHW) PV compatibility table concerns use case 2; it does not establish an additional Modbus map. Likewise, Altherma 4's direct Modbus and HomeHub EEBUS features do not establish compatibility with these maps. Neither is offered as a profile.

Published support is separate from physical verification, which is pending for all profiles. The map cannot discover model, Micon ID, firmware, accessories or installer settings. Select the compatibility profile explicitly and enable optional functions deliberately.
