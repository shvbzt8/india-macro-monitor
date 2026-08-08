# India Economic Monitor

An interactive Streamlit dashboard for monitoring India’s economic and financial health through clear, data-driven visualizations.

The project currently focuses on Consumer Price Index (CPI) inflation across Indian states and union territories. It is intended to grow into a broader economic-monitoring platform covering output, prices, employment, public finances, trade, monetary conditions, and financial markets.

## Live Dashboard

[Open the India Economic Monitor](https://shvbzt8-india-macro-monitor-ind-eco-g6tjwf.streamlit.app/)



## Current Features

- Interactive state-wise CPI inflation map
- Month and year selection
- Consumer item-group selection
- State and union territory comparisons
- Ranking of the five states with the highest inflation
- Rural, urban, and combined-sector comparison
- All-India CPI level and inflation time series
- Interactive Plotly charts with hover information
- Responsive Streamlit dashboard layout

## Indicators Currently Covered

### Consumer Price Index

The current version presents:

- State-wise year-on-year CPI inflation
- Rural CPI inflation
- Urban CPI inflation
- Combined CPI inflation
- CPI index levels
- Inflation trends over time
- Inflation across consumption divisions

## Planned Expansion

Future versions may include:

- Gross Domestic Product growth
- Industrial production
- Employment and unemployment
- Government revenue and expenditure
- Fiscal deficit and public debt
- Merchandise exports and imports
- Current account indicators
- Repo rate and monetary-policy indicators
- Banking and credit growth
- Exchange rates
- Equity-market indicators
- Foreign investment flows
- Commodity and energy prices
- Forecasts for CPI inflation and other major economic indicators
- Forecast ranges and uncertainty intervals

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- Matplotlib
- OpenPyXL
- GeoJSON
- Git and GitHub

## Project Structure

```text
india-economic-monitor/
├── .streamlit/
│   └── config.toml
├── India_LGD_states.geojson
├── cpi_6.xlsx
├── ind_eco.py
├── requirements.txt
├── README.md
└── .gitignore
```

Development notebooks may also be present in the repository. They are used for data exploration and testing rather than running the deployed application.

## Data Sources

The dashboard uses data obtained from official Indian statistical sources.

- Consumer Price Index data: Ministry of Statistics and Programme Implementation, Government of India
- State and union territory boundaries: India Local Government Directory GeoJSON dataset

Users should consult the original source publications for official definitions, methodology, revisions, and the latest observations.

## Limitations

- The current release focuses primarily on CPI inflation.
- The data-update process is not yet automated.
- Some indicators may be published with a delay.
- Official statistics may be revised after their initial release.
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
