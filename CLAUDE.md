# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Focus Financier** is a Streamlit web application for analyzing French municipality financial data. It fetches data from the French government's open data API (data.economie.gouv.fr) and provides interactive visualizations comparing municipalities to their strata averages.

The application features:
- Multi-year financial analysis (2019-2024)
- Six analysis modules: Fonctionnement, CAF, Fiscalité, Endettement, Investissement, Fonds de roulement
- PDF/Excel/CSV export capabilities
- Intelligent commune name variant handling (e.g., "LA ROCHELLE" vs "ROCHELLE (LA)")

## Running the Application

**Start the app:**
```bash
streamlit run prod.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

The app runs on `http://localhost:8501` by default.

## Architecture

### Entry Point & Navigation
- **prod.py**: Main application entry point. Handles the homepage with commune selection, year filters, and coordinates all export functionality (PDF/Excel/CSV). Contains extensive PDF generation logic with matplotlib charts.
- **api.py**: Legacy/alternative entry point (appears obsolete based on README)

### Data Layer
- **app_fetchers.py**: Core data fetching module containing `AppRobustFetcher` class and all fetch functions:
  - `fetch_commune_fonctionnement()`, `fetch_commune_caf()`, `fetch_commune_fiscalite()`, etc.
  - Implements commune name normalization and variant searching (handles articles like "LA", "LE", "LES")
  - Uses `@st.cache_resource` for the fetcher instance and `@lru_cache` for name normalization
  - Handles year-to-dataset mapping via `DATASETS_MAPPING` dict

### Dataset Mapping Strategy
The API uses different datasets for different year ranges:
```python
DATASETS_MAPPING = {
    2019: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2020: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2021: "comptes-individuels-des-communes-fichier-global-2021",
    2022: "comptes-individuels-des-communes-fichier-global-2022",
    2023: "comptes-individuels-des-communes-fichier-global-2023-2024",
    2024: "comptes-individuels-des-communes-fichier-global-2023-2024"
}
```
Functions like `get_dataset_for_year()` and `get_api_url_for_year()` handle dataset selection automatically.

### Pages Module
Each analysis module in `pages/` follows the same pattern:
- Defines a `run(commune, annees, departement)` function
- Called from prod.py with session state parameters
- Implements its own data fetching, table display, and Plotly visualization
- Pages: `fonctionnement.py`, `caf.py`, `fiscalite.py`, `endettements.py`, `investissements.py`, `fdr.py`

### Session State Management
prod.py uses `st.session_state` to maintain:
- `commune`: Selected commune name
- `departement`: Department code
- `annees`: List of years to analyze (default: 2019-2024)

### Commune Name Handling
The `AppRobustFetcher` class in app_fetchers.py handles commune name variants:
- Normalizes names with `normalize_commune_name()` using regex patterns
- Generates search terms via `_generate_search_terms()` (e.g., "LA ROCHELLE" → "ROCHELLE", "ROCHELLE (LA)")
- Uses fuzzy matching with `SequenceMatcher` (80% threshold)
- Searches across all datasets to find valid variants
- Caches results for performance

### Export Features
PDF generation in prod.py (`create_pdf_report()`):
- Uses ReportLab for document structure
- Creates matplotlib/seaborn charts via `create_chart_image()`
- Generates a comprehensive report with executive summary, all modules, and methodology notes
- Manages temporary image files for chart inclusion

Excel export (`create_excel_report()`):
- Uses openpyxl engine
- Creates 7 sheets: Synthèse + 6 module sheets
- Merges data from all modules for the synthesis sheet

### Caching Strategy
- `@st.cache_data(show_spinner=False)`: For API data results (`search_commune`, `get_all_commune_data`)
- `@st.cache_resource`: For the `AppRobustFetcher` instance
- `@lru_cache(maxsize=500)`: For commune name normalization
- Manual dict-based cache in `AppRobustFetcher._cache` for commune variants

## API Integration

**Base API:** `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/{dataset}/records`

**Query structure:**
- Uses `where` parameter with dataset-specific field names (e.g., `inom` for commune name, `an` for year, `dep` for department)
- Field names used: `inom`, `an`, `dep`, `pop1`, `prod`, `charge`, `fprod`, `mprod`, etc.
- Each module fetches different field combinations

**Typical fetch pattern:**
1. Get dataset URL for specific year
2. Try each commune name variant
3. Build `where` clause with year + commune + optional department
4. Parse results into DataFrame
5. Rename columns to French display names
6. Calculate ratios (e.g., personnel/DRF, CAF/RRF)

## Common Column Naming Patterns

**Raw API fields:**
- `an`: Année (year)
- `inom`: Nom de la commune (commune name)
- `dep`: Département (department)
- `pop1`: Population
- `fprod`, `mprod`: Commune value vs mean strata (for various metrics)
- `f*` prefix: Commune-specific values (e.g., `fcaf`, `fdette`)
- `m*` prefix: Strata mean values (e.g., `mcaf`, `mdette`)

**Display names:** Fully translated French names (e.g., "Recettes réelles fonctionnement / hab")

## Testing & Development

No formal test suite is present. The `test.py` file appears to contain experimentation code rather than unit tests.

For manual testing:
1. Start the app with `streamlit run prod.py`
2. Enter a commune name in ALL CAPS (e.g., "RENAGE", "PARIS")
3. Select years and navigate through modules
4. Test export features from the homepage

## Known Quirks

- Commune names must be entered in UPPERCASE
- The app handles homonyms by showing a dropdown selector
- Some communes may have missing data for certain years (API data availability)
- PDF generation requires `kaleido` package (auto-installs in prod.py if missing)
- Matplotlib charts are generated as temporary PNG files during PDF creation

## Files Not Part of Main Application Flow

- **MFF.py**: Purpose unclear, not imported by main app
- **epci.py**: Appears to be EPCI (intercommunal) analysis code (separate from main app)
- **test.py**: Contains experimental/testing code
- **packages.txt**: System package dependencies (likely for deployment)
- **.devcontainer/**: Dev container configuration
