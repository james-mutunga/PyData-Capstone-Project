# Safaricom vs Airtel: Which gives better value for mobile data?

A data analysis project comparing mobile data bundles from Safaricom and Airtel in Kenya. The goal is to find out which network offers better value for money, across daily, weekly, and monthly bundles.

## The question

Which network gives better value for mobile data?

I answer this in three parts:

1. At each price, which network gives more data?
2. For a real person, which network costs less per month?
3. Which network has better 4G coverage where people live?

## What's in this project

- **`Data-bundles.ipynb`** — the full analysis notebook
- **`requirements.txt`** — the Python libraries needed to run it
- **`Data/kenyan-counties/`** — the shapefile and tower data used in the coverage section

## How the analysis works

1. **Price per GB** — how much each GB costs, across every tier
2. **Head-to-head** — how much more data Airtel gives at the same price
3. **Cost to cover a month** — the cheapest way for a real person to cover 30 days
4. **Price per GB actually used** — the real cost when you don't use everything you bought
5. **Coverage** — where each network has 4G towers, by county

## Key findings

- **Airtel is cheaper per GB in every tier.**
- **Airtel gives 9–60% more data at the same price.**
- **For a real person, Airtel saves KES 500–1,000 a month.**
- **Safaricom has 4G towers in 34 of 47 counties; Airtel in 25.**
- **Safaricom has more towers in 32 counties; Airtel in only 2.**

The real answer depends on where you live: if you have good Airtel signal, Airtel gives better value. If not, Safaricom's higher prices buy you coverage.

## Limits

- 16 bundles, one day's prices, 4G only
- Usage needs are estimates, not measurements
- Not everyone has a 4G smartphone — see the notebook's Context section

## Data sources

- **Bundle prices:** USSD code `*544#` for both networks (as of 11 October 2026)
- **County boundaries:** Kenya county shapefile
- **4G tower locations:** OpenCelliD (opencellid.org)
- **Context data:** Communications Authority of Kenya, Q2 2025/26 Sector Statistics Report (December 2025)

## How to run this

1. Install the required libraries: `pip install -r requirements.txt`
2. Open the notebook: `jupyter notebook Data-bundles.ipynb`
3. Run all cells: `Cell → Run All`

## Author

James Mutunga