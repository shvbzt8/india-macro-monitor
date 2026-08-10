# India Economic Monitor

An interactive Streamlit dashboard for monitoring India’s economic and financial health through clear, data-driven visualizations.

The project currently focuses on Consumer Price Index (CPI) inflation across Indian states and union territories. It is intended to grow into a broader economic-monitoring platform covering output, prices, employment, public finances, trade, monetary conditions, and financial markets.

## Live Dashboard

[Open the India Economic Monitor](https://shvbzt8-india-macro-monitor-ind-eco-g6tjwf.streamlit.app/)



## Current Features

An interactive, filterable view of CPI inflation: a state-wise choropleth map, a bar chart ranking the five states with the highest inflation, and an All-India level-vs-inflation time series, each split by rural/urban/combined sector and by consumption item group. A sidebar toggle switches the whole dashboard between two CPI series:

- **Current series** (base 2024 = 100): monthly from January 2025 onward, synced automatically.
- **Historical series** (base 2012 = 100): January 2013 through December 2025, MoSPI's prior methodology, kept as a frozen archive since it's no longer being updated.

Charts are built with Plotly and support hover tooltips; the layout is responsive within Streamlit's page width.

## Indicators Currently Covered

Consumer Price Index only, for now: index levels and year-on-year inflation, by state/UT, sector, and consumption division, across both series described above.

## Planned Expansion

The roadmap extends beyond CPI toward a fuller economic-monitoring platform: real-sector indicators (GDP growth, industrial production, employment), fiscal indicators (government revenue/expenditure, deficit, public debt), external-sector indicators (trade, current account, exchange rates, foreign investment), monetary and financial indicators (repo rate, credit growth, equity markets, commodity prices), and CPI forecasts with uncertainty ranges.

## Technology Stack

Python (Streamlit, Pandas, Plotly, Matplotlib, Requests, PyArrow) for the app and data pipeline, GeoJSON for map boundaries, and Git/GitHub with GitHub Actions for version control and scheduled syncs.

## Project Structure

```text
india-economic-monitor/
├── .github/
│   └── workflows/
│       └── sync_cpi_data.yml
├── .streamlit/
│   └── config.toml
├── India_LGD_states.geojson
├── cpi_data.parquet
├── fetch_cpi.py
├── ind_eco.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Data Sources

The dashboard uses data obtained from official Indian statistical sources.

- Consumer Price Index data: Ministry of Statistics and Programme Implementation, Government of India, via the [eSankhyiki](https://esankhyiki.mospi.gov.in/) API
- State and union territory boundaries: India Local Government Directory GeoJSON dataset

Users should consult the original source publications for official definitions, methodology, revisions, and the latest observations.

## Data Pipeline

`fetch_cpi.py` syncs `cpi_data.parquet` from the MoSPI eSankhyiki API via the [`mospi-esankhyiki`](https://pypi.org/project/mospi-esankhyiki/) client library. The current series is refreshed monthly by a GitHub Actions workflow (`.github/workflows/sync_cpi_data.yml`), which commits the updated dataset back to the repository; Streamlit Cloud then redeploys automatically, so the live dashboard stays current without manual intervention. The historical series was a one-time backfill and isn't part of that recurring sync, since MoSPI no longer publishes new data for it.

The API has no server-side way to request only the top-level (division/group) rows — filtering by division or group also returns every finer category beneath it. `fetch_cpi.py` pages through the requested months and keeps the top-level rows client-side, which is why syncs are done per month rather than as a single bulk pull.

## Limitations

- The current release focuses primarily on CPI inflation.
- The historical series (base 2012) predates a couple of union-territory mergers/splits and isn't published state-wise for every division, so a few state/division combinations show no data on the map — this reflects the original MoSPI data, not a pipeline gap.
- Some indicators may be published with a delay, and official statistics may be revised after their initial release.
- Geographic boundary data are used only for visualization.

## Disclaimer

This project is intended for educational, research, and informational purposes. It does not provide financial, investment, legal, or policy advice.

Although the dashboard aims to use reliable sources, users should verify important figures against the latest official publications before relying on them.

## Contributing

Suggestions, corrections, and contributions are welcome.

To propose a change:

1. Fork the repository.
2. Create a feature branch.
3. Make and test the changes.
4. Commit the changes.
5. Open a pull request describing the improvement.

## Author

**Shivam Bist**

## License

No license has been assigned yet. Unless a license file is added, the repository’s contents remain protected under standard copyright rules.
