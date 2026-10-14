# ---------------------------------------------------------------
# Safaricom vs Airtel — Streamlit app
# Tab 1: Price per GB
# Tab 2: Cost for a real person (with slider)
# Tab 3: Coverage
# Tab 4: Context
# ---------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Safaricom vs Airtel", layout="wide")
st.title("Safaricom vs Airtel: Which gives better value for mobile data?")

# --- The bundles dataset ---
bundles = pd.DataFrame([
    ["Safaricom", "Sh99=1.5GB+40SMS+BAZE,24hrs",   99,  1.5, "daily"],
    ["Safaricom", "Sh99=1.1GB+Free YouTube 7day",  99,  1.1, "weekly"],
    ["Safaricom", "Sh250=3.2GB+Free YouTube 7day", 250, 3.2, "weekly"],
    ["Safaricom", "Sh500=11GB+Free YouTube 7day",  500, 11, "weekly"],
    ["Safaricom", "Sh250=2.5GB 30day",             250,  2.5, "monthly"],
    ["Safaricom", "Sh500=7GB+WhatsApp 30day",      500,  7, "monthly"],
    ["Safaricom", "Sh1000=21GB+WhatsApp 30day",   1000, 21, "monthly"],
    ["Safaricom", "Sh2000=45GB+WhatsApp 30day",   2000, 45, "monthly"],
    ["Airtel", "2.4GB+WhatsApp @99",      99,  2.4, "daily"],
    ["Airtel", "1.5GB+WhatsApp @100,7days",  100,  1.5, "weekly"],
    ["Airtel", "5GB+WhatsApp @250,7days",    250,  5, "weekly"],
    ["Airtel", "12GB+WhatsApp @500,7days",   500, 12, "weekly"],
    ["Airtel", "3GB @250",     250,  3, "monthly"],
    ["Airtel", "8GB @500",     500,  8, "monthly"],
    ["Airtel", "25GB @1000",  1000, 25, "monthly"],
    ["Airtel", "55GB @2000",  2000, 55, "monthly"],
], columns=["provider", "bundle_name", "price_kes", "data_gb", "validity"])

bundles["price_per_gb"] = (bundles["price_kes"] / bundles["data_gb"]).round(2)
validity_days = {"daily": 1, "weekly": 7, "monthly": 30}
bundles["validity_days"] = bundles["validity"].map(validity_days)

# ---------------------------------------------------------------
# Coverage data — cached so it loads once
# ---------------------------------------------------------------
@st.cache_data
def load_coverage():
    counties = gpd.read_file("Data/kenyan-counties/County.shp")
    counties = counties.to_crs("EPSG:4326")
    county_col = "COUNTY"

    cols = ["radio", "mcc", "net", "area", "cell", "unit", "lon", "lat",
            "range", "samples", "changeable", "created", "updated", "averageSignal"]
    chunks = []
    for chunk in pd.read_csv("Data/kenyan-counties/639.csv.gz", header=None, names=cols,
                             usecols=["radio", "mcc", "net", "lon", "lat"],
                             chunksize=1_000_000):
        keep = chunk[(chunk["mcc"] == 639) & (chunk["radio"] == "LTE")]
        chunks.append(keep)
    towers = pd.concat(chunks, ignore_index=True)
    towers["provider"] = towers["net"].map({2: "Safaricom", 3: "Airtel"})
    towers = towers.dropna(subset=["provider"])

    tower_points = gpd.GeoDataFrame(
        towers,
        geometry=gpd.points_from_xy(towers["lon"], towers["lat"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(tower_points, counties[[county_col, "geometry"]],
                       how="inner", predicate="within")
    tower_counts = joined.groupby([county_col, "provider"]).size().unstack(fill_value=0)
    tower_counts = tower_counts.reindex(counties[county_col].unique(), fill_value=0)
    tower_counts = tower_counts[["Safaricom", "Airtel"]]

    counties["area_km2"] = counties.to_crs("EPSG:6933").area / 1_000_000
    coverage = counties.merge(tower_counts, left_on=county_col, right_index=True)
    for name in ["Safaricom", "Airtel"]:
        coverage[f"{name}_per_1000km2"] = (coverage[name] / coverage["area_km2"] * 1000).round(2)
    coverage["total_towers"] = coverage["Safaricom"] + coverage["Airtel"]

    return coverage, county_col

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Price per GB", "Cost for a real person", "Coverage", "Context"])

# ---------------------------------------------------------------
# Tab 1 — Price per GB
# ---------------------------------------------------------------
with tab1:
    st.header("Price per GB")
    st.write("How much does each GB cost? Lower is better.")

    validity_choice = st.selectbox("Choose a validity:", ["daily", "weekly", "monthly"])
    filtered = (bundles[bundles["validity"] == validity_choice]
                .sort_values("price_per_gb").reset_index(drop=True))

    col1, col2 = st.columns([2, 1])
    with col1:
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = ["green" if p == "Safaricom" else "red" for p in filtered["provider"]]
        bars = ax.barh(filtered["bundle_name"], filtered["price_per_gb"], color=colors)
        ax.bar_label(bars, labels=[f"KES {v}" for v in filtered["price_per_gb"]], padding=3)
        ax.set_xlabel("Price per GB (KES)")
        ax.invert_yaxis()
        ax.set_title(f"{validity_choice.title()} bundles — price per GB")
        st.pyplot(fig)

    with col2:
        st.write("**Full table**")
        st.dataframe(filtered[["provider", "bundle_name", "price_kes", "data_gb", "price_per_gb"]],
                     hide_index=True, use_container_width=True)

    cheapest = filtered.iloc[0]
    st.success(f"Cheapest: **{cheapest['provider']} — {cheapest['bundle_name']}** "
               f"at **KES {cheapest['price_per_gb']} per GB**.")

# ---------------------------------------------------------------
# Tab 2 — Cost for a real person
# ---------------------------------------------------------------
with tab2:
    st.header("Cost for a real person")
    st.write("Move the slider to your monthly data need. The app works out "
             "the cheapest way each network can cover 30 days for that need.")

    need_gb = st.slider("Your monthly data need (GB):", min_value=5, max_value=100, value=59, step=1)

    def cost_to_cover(need):
        df = bundles.copy()
        # The minimum number of bundles to cover 30 days of access.
        df["min_bundles_for_days"] = np.ceil(30 / df["validity_days"]).astype(int)
        # The number of bundles you'd need to cover the data need.
        df["bundles_for_data"] = np.ceil(need / df["data_gb"]).astype(int)
        # Start from the minimum to cover 30 days.
        df["bundles_needed"] = df["min_bundles_for_days"]
        df["total_cost"] = df["bundles_needed"] * df["price_kes"]
        df["total_gb"] = (df["bundles_needed"] * df["data_gb"]).round(1)

        # If the min bundles don't cover the data need, add more bundles,
        # but only up to one extra validity period past 30 days.
        def try_extend(row):
            bundles = row["bundles_needed"]
            max_bundles = np.ceil((30 + row["validity_days"]) / row["validity_days"])
            while bundles * row["data_gb"] < need and bundles < max_bundles:
                bundles += 1
            if bundles * row["data_gb"] < need:
                return np.nan
            return bundles

        df["bundles_needed"] = df.apply(try_extend, axis=1)
        df = df.dropna(subset=["bundles_needed"])
        df["bundles_needed"] = df["bundles_needed"].astype(int)
        df["total_cost"] = df["bundles_needed"] * df["price_kes"]
        df["total_gb"] = (df["bundles_needed"] * df["data_gb"]).round(1)
        return df

    df = cost_to_cover(need_gb)
    best = (df.sort_values(["total_cost", "total_gb"], ascending=[True, False])
              .groupby("provider").first().loc[["Safaricom", "Airtel"]])

    # Show which bundle is used
    st.write("**Cheapest option per network:**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Safaricom", f"KES {best.loc['Safaricom', 'total_cost']:,.0f}",
                  f"{best.loc['Safaricom', 'total_gb']:.0f} GB")
        st.caption(f"{int(best.loc['Safaricom', 'bundles_needed'])} × "
                   f"{best.loc['Safaricom', 'bundle_name']}")
    with col2:
        st.metric("Airtel", f"KES {best.loc['Airtel', 'total_cost']:,.0f}",
                  f"{best.loc['Airtel', 'total_gb']:.0f} GB")
        st.caption(f"{int(best.loc['Airtel', 'bundles_needed'])} × "
                   f"{best.loc['Airtel', 'bundle_name']}")

    # Chart
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(best.index, best["total_cost"], color=["green", "red"])
    ax.bar_label(bars, labels=[f"KES {c:,.0f}\n{g:.0f} GB"
                               for c, g in zip(best["total_cost"], best["total_gb"])])
    ax.set_ylabel("Cheapest cost for 30 days (KES)")
    ax.set_title(f"Cost to cover {need_gb} GB a month")
    ax.margins(y=0.2)
    st.pyplot(fig)

    gap = best.loc["Safaricom", "total_cost"] - best.loc["Airtel", "total_cost"]
    if gap > 0:
        st.success(f"Airtel is cheaper by **KES {gap:,.0f}** for {need_gb} GB a month.")
    else:
        st.info("Both networks cost the same for this need.")

# ---------------------------------------------------------------
# Tab 3 — Coverage
# ---------------------------------------------------------------
with tab3:
    st.header("Coverage: where does each network have 4G towers?")
    st.write("Darker means more towers per 1,000 km². Green is Safaricom, red is Airtel.")

    coverage, county_col = load_coverage()

    both = pd.concat([coverage["Safaricom_per_1000km2"], coverage["Airtel_per_1000km2"]])
    top = np.percentile(both, 90)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    coverage.plot(column="Safaricom_per_1000km2", cmap="Greens", vmin=0, vmax=top,
                  legend=True, edgecolor="grey", linewidth=0.3, ax=axes[0])
    axes[0].set_title("Safaricom: 4G towers per 1,000 km²")
    coverage.plot(column="Airtel_per_1000km2", cmap="Reds", vmin=0, vmax=top,
                  legend=True, edgecolor="grey", linewidth=0.3, ax=axes[1])
    axes[1].set_title("Airtel: 4G towers per 1,000 km²")
    for ax in axes:
        ax.axis("off")
    st.pyplot(fig)

    st.subheader("Look up a county")
    county_choice = st.selectbox("Pick a county:",
                                 sorted(coverage[county_col].unique()))
    row = coverage[coverage[county_col] == county_choice].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Safaricom towers", int(row["Safaricom"]))
    with col2:
        st.metric("Airtel towers", int(row["Airtel"]))
    with col3:
        if row["Safaricom"] > row["Airtel"]:
            st.metric("Who has more", "Safaricom")
        elif row["Airtel"] > row["Safaricom"]:
            st.metric("Who has more", "Airtel")
        else:
            st.metric("Who has more", "Equal")

    st.subheader("Top 15 counties by total towers")
    top15 = coverage.nlargest(15, "total_towers").set_index(county_col)[["Safaricom", "Airtel"]]

    fig2, ax2 = plt.subplots(figsize=(8, 6))
    top15.plot(kind="barh", color=["green", "red"], ax=ax2)
    ax2.invert_yaxis()
    ax2.set_xlabel("4G towers found")
    ax2.set_ylabel("")
    ax2.set_title("Top 15 counties by 4G towers")
    st.pyplot(fig2)

# ---------------------------------------------------------------
# Tab 4 — Context
# ---------------------------------------------------------------
with tab4:
    st.header("Context: who this analysis is for, and who it isn't")
    st.write("Everything in this app assumes one kind of user: someone with a **4G smartphone** "
             "who can buy data bundles from `*544#`. This tab looks at who is left out of the analysis.")

    st.subheader("My bias")
    st.markdown("""
**I am pro-Airtel.** I use Airtel personally and it works well where I live. I also find Safaricom's
bundles overpriced — I'd rather get more data on Airtel for the same money. That's a preference,
not a fact.

Where it might have shown up: the bundles I picked, how I framed the results, and which network
I present as the winner.

What I did to limit it:

- I picked bundles that **cost the same on both networks**, so the only difference is what you get for your money.
- I left out one-off promotional bundles — they change too often to compare fairly.
- All the calculations are in the notebook, so you can check them.
    """)

    st.subheader("Device access in Kenya")
    st.markdown("""
Almost every Kenyan household has a mobile phone:

- **93.8%** own at least one mobile phone
- **95.8%** use at least one mobile phone

But **owning a phone is not the same as owning a smartphone**. As of December 2025, Kenya had
**78.3 million mobile phones** on its networks:

- **48.7 million smartphones**
- **29.6 million feature phones**

Only about **62%** of phones are smartphones — the kind this analysis assumes.

**Source:** Communications Authority of Kenya, Q2 2025/26 Sector Statistics Report (December 2025).
    """)

    st.subheader("Network generation: not everyone is on 4G")
    st.markdown("""
As of December 2025, Kenya's mobile data subscriptions were:

| Network | Subscriptions | Share |
|---------|---------------|-------|
| **4G** | 44.2 million | 71.2% |
| **2G** | 10.4 million | 16.8% |
| **3G** | 5.7 million | 9.1% |
| **5G** | 1.7 million | 2.8% |

4G is the clear majority — but more than **16 million people** are still on 2G or 3G. Many of them
live in rural areas, use older phones, or buy smaller bundles.
    """)

    st.subheader("County bias: the digital divide")
    st.markdown("""
Even among people with 4G smartphones, the experience is not the same across Kenya. The most
underserved counties are in the north and northeast.

**Lowest internet usage** (share of households):

| County | Households using internet |
|--------|---------------------------|
| West Pokot | 9.1% |
| Turkana | 12.7% |
| Tana River | 15.5% |
| Marsabit | 16.3% |
| Garissa | 16.5% |

Compare to: **Nairobi at 64.7%**. That's about **7 times** higher.
    """)

    st.subheader("What this means for my analysis")
    st.markdown("""
My findings apply most directly to **one kind of user**: someone with a 4G smartphone, with
coverage where they live, buying standard daily, weekly, or monthly bundles.

For everyone else, the picture is more complicated:

- **Feature phone users** (about 29.6 million) can't use these bundles the same way.
- **2G and 3G users** (about 16 million) buy smaller bundles and use less data.
- **People in underserved counties** pay the same prices but may get worse signal.

So when I say "Airtel gives more data per shilling," that's true for the bundles I compared and
the users I assumed. It isn't automatically true for every Kenyan.
    """)