# DATA\_LICENSES.md

This document clarifies what third‑party data we reference and how we comply with their terms. We **do not redistribute** any third‑party problem statements or proprietary test files. The repository contains **IDs and lightweight metadata only** (see `configs/bigobench.json`, `configs/codeforces.json`).

> **Scope of our release**
>
> * We release code (MIT license), configuration files, seeds, logs we generate, figures, and scripts.
> * For third‑party datasets/online judges, we provide **problem IDs** and instructions to let users retrieve materials from the official sources under their terms.

---

## 1) BigO(Bench)

* **What we include**: A list of task IDs and minimal metadata sufficient to identify tasks in BigO(Bench) (e.g., `BIGOBENCH_1718`).
* **What we do not include**: Full problem statements, editorial text, or any copyrighted assets owned by the dataset authors.
* **How to use**: The evaluation pipeline reads the IDs from `configs/bigobench.json`. If textual statements or input files are needed locally, please obtain them directly from the original source(s) in accordance with the dataset authors’ license and terms of use.
* **Attribution**: Please cite the BigO(Bench) authors as instructed by the dataset documentation.
* **Compliance note**: Users are responsible for following all license/ToS requirements of BigO(Bench) when retrieving or using its materials.

---

## 2) Codeforces

* **What we include**: Codeforces problem IDs (e.g., `CF1285A`) and lightweight metadata (difficulty rating, tags).
* **What we do not include**: Problem statements, editorial content, or proprietary input/output files.
* **How to use**: Our evaluation uses IDs from `configs/codeforces.json`. If you wish to view statements or run your own I/O locally, obtain them from Codeforces in accordance with its Terms of Service.
* **Attribution**: Codeforces is operated by its respective owners; please follow Codeforces’ rules for usage, attribution, and rate‑limits.
* **Compliance note**: Users must abide by Codeforces’ ToS and should not scrape or redistribute content in violation of the site’s policies.

---

## 3) AtCoder (not used in task lists for this release)

* We reference AtCoder as a related source in the paper, but **no AtCoder problems are included** in the task indices shipped with this artifact.
* If you extend experiments to AtCoder, please obtain tasks from the official site and follow AtCoder’s ToS and licensing rules.

---

## 4) Our assets (licenses)

* **Code**: Licensed under **MIT** (see `LICENSE`).
* **Logs / figures / tables**: Released under **CC‑BY‑4.0** unless otherwise noted. If you prefer a different license for your logs post‑review (e.g., CC0), update this file and the figure headers accordingly.
* **Third‑party Python packages**: Governed by their respective licenses as listed in `requirements.txt` / `requirements.lock`.

---

## 5) Compliance checklist for users

1. Use problem **IDs** from `configs/*.json` to locate tasks on the official sites.
2. Read and follow each site’s **Terms of Service** and **license** before downloading or reusing content.
3. Do **not** redistribute third‑party problem statements or proprietary test files as part of derived artifacts.
4. When publishing results obtained with third‑party tasks, include appropriate **citations/attributions**.
5. Respect **rate limits** and fair‑use policies of online judges.

---

## 6) Contact

For issues related to data licensing and compliance in this anonymous release, please open an issue in the repository. We will update this file if any upstream license/ToS changes need to be reflected.
