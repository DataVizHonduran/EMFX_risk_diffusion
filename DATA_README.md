# FX Data Export Documentation

This repository automatically generates and updates two CSV files containing foreign exchange data that can be used for other projects.

## Available Data Files

### 1. `fx_data_raw.csv`
**Description:** Raw daily close prices for all tracked currencies quoted as USD/XXX.

**Format:**
- Index: Date (YYYY-MM-DD)
- Columns: Currency codes (EUR, AUD, CAD, GBP, JPY, SEK, NOK, NZD, CHF, MXN, CLP, BRL, COP, PEN, KRW, IDR, INR, THB, PHP, SGD, PLN, HUF, CZK, ZAR, TRY)
- Values: Exchange rate (how many units of foreign currency per 1 USD)

**Data Source:** Alpha Vantage FX Daily API
**Update Frequency:** Daily at 12:00 UTC (Mon-Fri)
**Historical Coverage:** Full history available from Alpha Vantage

**Example Usage:**
```python
import pandas as pd

# Load raw FX data
fx_raw = pd.read_csv('fx_data_raw.csv', index_col=0, parse_dates=True)

# Get USDMXN exchange rate
usdmxn = fx_raw['MXN']

# Calculate returns
returns = fx_raw.pct_change()
```

### 2. `fx_data_emfx.csv`
**Description:** Processed emerging market FX data with inverted quotes (XXX/USD) showing local currency strength, filtered from 2014-11-01 onwards.

**Format:**
- Index: Date (YYYY-MM-DD, starting from 2014-11-01)
- Columns: Emerging market currency codes (MXN, CLP, BRL, COP, PEN, KRW, IDR, INR, THB, PHP, SGD, PLN, HUF, CZK, ZAR, TRY)
- Values: Inverted exchange rate (1 / USD/XXX), with forward-fill and backward-fill applied

**Data Source:** Derived from `fx_data_raw.csv`
**Update Frequency:** Daily at 12:00 UTC (Mon-Fri)
**Historical Coverage:** From 2014-11-01 to present

**Processing Steps:**
1. Filter to EM currencies only
2. Invert quotes (1 / USDXXX) to show local currency strength
3. Apply backward-fill then forward-fill to handle missing data
4. Filter to dates from 2014-11-01 onwards

**Example Usage:**
```python
import pandas as pd

# Load processed EM FX data
emfx = pd.read_csv('fx_data_emfx.csv', index_col=0, parse_dates=True)

# Calculate EM FX index (equal-weighted average)
em_index = emfx.mean(axis=1)

# Get Brazilian Real strength vs USD
brl_strength = emfx['BRL']
```

## Currency Coverage

### Developed Markets (DM)
EUR, AUD, CAD, GBP, JPY, SEK, NOK, NZD, CHF

### Emerging Markets (EM)
- **Latin America:** MXN, CLP, BRL, COP, PEN
- **Asia:** KRW, IDR, INR, THB, PHP, SGD
- **EMEA:** PLN, HUF, CZK, ZAR, TRY

## Accessing the Data

### Option 1: Direct Download from GitHub
```bash
# Download raw data
curl -O https://raw.githubusercontent.com/DataVizHonduran/EMFX_risk_diffusion/main/fx_data_raw.csv

# Download processed EM data
curl -O https://raw.githubusercontent.com/DataVizHonduran/EMFX_risk_diffusion/main/fx_data_emfx.csv
```

### Option 2: Clone Repository
```bash
git clone https://github.com/DataVizHonduran/EMFX_risk_diffusion.git
cd EMFX_risk_diffusion
```

### Option 3: Use in Python with pandas
```python
import pandas as pd

# Load directly from GitHub
raw_url = 'https://raw.githubusercontent.com/DataVizHonduran/EMFX_risk_diffusion/main/fx_data_raw.csv'
fx_raw = pd.read_csv(raw_url, index_col=0, parse_dates=True)

emfx_url = 'https://raw.githubusercontent.com/DataVizHonduran/EMFX_risk_diffusion/main/fx_data_emfx.csv'
fx_emfx = pd.read_csv(emfx_url, index_col=0, parse_dates=True)
```

## Data Quality Notes

- Missing data is handled via backward-fill and forward-fill in the EM FX dataset
- Exchange rates are daily close prices
- Data updates Monday-Friday at 12:00 UTC via GitHub Actions
- Raw data includes weekends/holidays where available from Alpha Vantage
- Alpha Vantage API rate limits may occasionally cause delays in updates

## License

This data is provided for informational and research purposes. Please review the repository license for usage terms.

## Attribution

Data sourced from Alpha Vantage (https://www.alphavantage.co/)
Processing and analysis by DataVizHonduran
