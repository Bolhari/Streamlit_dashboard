"""
This is our Sales Dashboard from our last session.
Run locally: First run it locally using Streamlit and Colab (run app.py)
Deploy: Then, push this to your GitHub, and deploy app.py on share.streamlit.io

Your repo layout:
    app.py
    requirements.txt
    data/sales_data.csv
    README.md
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page setup (must be the first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Sales Dashboard", page_icon=":material/bar_chart:", layout="wide")

# A path relative to THIS file works in Colab, on your laptop and on Streamlit Cloud.
# (A hard-coded path such as /content/sales_data.csv only works in Colab.)
DATA_PATH = Path(__file__).parent / "data" / "sales_data.csv"


# ---------------------------------------------------------------------------
# 1. Load and prepare data (cached: runs once, not on every rerun)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])

    # IDs are labels, not numbers: as integers, charts would draw them on a
    # continuous axis (e.g. "Product 3000.5"), so convert them to text.
    for col in ["Transaction ID", "Customer ID", "Product ID"]:
        df[col] = df[col].astype(str)

    # Derived columns
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    df["Unit Price"] = (df["Revenue"] / df["Quantity Sold"]).round(2)
    return df


def filter_data(df: pd.DataFrame, regions, products, start, end) -> pd.DataFrame:
    mask = (
        df["Region"].isin(regions)
        & df["Product ID"].isin(products)
        & df["Date"].between(pd.Timestamp(start), pd.Timestamp(end))
    )
    return df[mask]


def kpi_row(df: pd.DataFrame) -> None:
    revenue = df["Revenue"].sum()
    units = int(df["Quantity Sold"].sum())
    orders = len(df)
    aov = revenue / orders if orders else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total revenue", f"£{revenue:,.0f}")
    c2.metric("Units sold", f"{units:,}")
    c3.metric("Transactions", f"{orders:,}")
    c4.metric("Avg order value", f"£{aov:,.2f}")


df = load_data(DATA_PATH)

# ---------------------------------------------------------------------------
# 2. Sidebar filters. Every widget change reruns this whole script.
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

all_regions = sorted(df["Region"].unique())
all_products = sorted(df["Product ID"].unique())

regions = st.sidebar.multiselect("Region", all_regions, default=all_regions)
products = st.sidebar.multiselect("Product", all_products, default=all_products)

date_range = st.sidebar.date_input(
    "Date range",
    value=(df["Date"].min().date(), df["Date"].max().date()),
    min_value=df["Date"].min().date(),
    max_value=df["Date"].max().date(),
)

# While the user is picking, date_input can return only one date.
if len(date_range) != 2:
    st.info("Select an end date to apply the date filter.")
    st.stop()
start, end = date_range

df_f = filter_data(df, regions, products, start, end)

# Guard against empty selections instead of crashing.
if df_f.empty:
    st.warning("No transactions match these filters. Widen your selection.")
    st.stop()

# ---------------------------------------------------------------------------
# 3. Page content
# ---------------------------------------------------------------------------
st.title("Welcome to Sales Dashboard")
st.caption(
    f"Showing {len(df_f)} of {len(df)} transactions · "
    f"{start:%d %b %Y} to {end:%d %b %Y}"
)

kpi_row(df_f)
st.divider()

tab_overview, tab_products, tab_customers, tab_data = st.tabs(
    ["Overview", "Products", "Customers", "Data"]
)

with tab_overview:
    left, right = st.columns(2)

    by_region = (
        df_f.groupby("Region", as_index=False)["Revenue"].sum()
        .sort_values("Revenue", ascending=False)
    )
    fig_region = px.bar(
        by_region, x="Region", y="Revenue", text_auto=".2s",
        title="Revenue by region", labels={"Revenue": "Revenue (£)"},
    )
    left.plotly_chart(fig_region, width="stretch")

    by_month = df_f.groupby("Month", as_index=False)["Revenue"].sum()
    fig_month = px.line(
        by_month, x="Month", y="Revenue", markers=True,
        title="Revenue by month", labels={"Revenue": "Revenue (£)", "Month": ""},
    )
    right.plotly_chart(fig_month, width="stretch")

    top_region = by_region.iloc[0]
    st.markdown(
        f"**Takeaway:** {top_region['Region']} brings in the most revenue "
        f"(£{top_region['Revenue']:,.0f}, "
        f"{top_region['Revenue'] / df_f['Revenue'].sum():.0%} of the selection)."
    )

with tab_products:
    by_product = (
        df_f.groupby("Product ID", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Units=("Quantity Sold", "sum"))
        .sort_values("Revenue", ascending=False)
    )
    fig_prod = px.bar(
        by_product, x="Product ID", y="Revenue", hover_data=["Units"],
        title="Revenue by product", labels={"Revenue": "Revenue (£)"},
    )
    st.plotly_chart(fig_prod, width="stretch")

    fig_scatter = px.scatter(
        df_f, x="Quantity Sold", y="Revenue", color="Region",
        hover_data=["Product ID", "Unit Price"],
        title="Comparison of sold quantities and revenue by each region",
        labels={"Revenue": "Revenue (£)"},
    )
    st.plotly_chart(fig_scatter, width="stretch")

    corr = df_f["Quantity Sold"].corr(df_f["Revenue"])
    st.markdown(
        f"**Data check:** the correlation between quantity and revenue is "
        f"{corr:.2f}."
    )

# with tab_customers:
#     st.caption(f"Showing top 5 customers")
#     top5_customers = (
#         df.groupby("Customer ID")["Revenue"]
#           .sum()
#           .sort_values(ascending=False)
#           .head(5)
#           .reset_index()
#     )

#     st.dataframe(top5_customers, use_container_width=True)


with tab_customers:

    # ---------- Customer-level summary (from the FILTERED data) ----------
    cust = (
        df_f.groupby("Customer ID")
            .agg(Revenue=("Revenue", "sum"),
                 Orders=("Transaction ID", "count"),
                 Units=("Quantity Sold", "sum"))
            .reset_index()
    )
    cust["Avg order value"] = (cust["Revenue"] / cust["Orders"]).round(2)
    # Each customer's most frequent region (used for colour)
    cust["Main region"] = (
        df_f.groupby("Customer ID")["Region"]
            .agg(lambda s: s.value_counts().idxmax())
            .values
    )

    # ---------- Top 5 table ----------
    st.subheader("Top 5 customers by revenue")
    top5 = cust.sort_values("Revenue", ascending=False).head(5)
    st.dataframe(
        top5[["Customer ID", "Revenue", "Orders", "Avg order value"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Revenue": st.column_config.ProgressColumn(
                "Revenue", format="£%.0f",
                min_value=0, max_value=float(cust["Revenue"].max())),
            "Avg order value": st.column_config.NumberColumn(format="£%.2f"),
        },
    )

    st.divider()

    # ---------- Chart 1: Customer segmentation bubble chart ----------
    med_orders = cust["Orders"].median()
    med_aov = cust["Avg order value"].median()

    fig_bubble = px.scatter(
        cust,
        x="Orders", y="Avg order value",
        size="Revenue", color="Main region",
        text="Customer ID",
        size_max=60,
        hover_data={"Revenue": ":,.2f", "Units": True},
        title="Customer segments: how often vs how much",
        labels={"Orders": "Number of orders",
                "Avg order value": "Average order value (£)"},
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig_bubble.update_traces(textposition="middle center",
                             textfont=dict(color="white", size=11),
                             marker=dict(line=dict(width=1, color="white"),
                                         opacity=0.85))
    # Median lines split the chart into four segments
    fig_bubble.add_vline(x=med_orders, line_dash="dash", line_color="grey")
    fig_bubble.add_hline(y=med_aov, line_dash="dash", line_color="grey")
    # Segment labels in each corner
    x_lo, x_hi = cust["Orders"].min(), cust["Orders"].max()
    y_lo, y_hi = cust["Avg order value"].min(), cust["Avg order value"].max()
    for x, y, label in [
        (x_hi, y_hi, "⭐ Champions"),
        (x_lo, y_hi, "💎 Big spenders"),
        (x_hi, y_lo, "🔁 Loyal regulars"),
        (x_lo, y_lo, "🌱 Grow these"),
    ]:
        fig_bubble.add_annotation(x=x, y=y, text=f"<b>{label}</b>",
                                  showarrow=False, opacity=0.6,
                                  font=dict(size=13))
    fig_bubble.update_layout(height=520)
    st.plotly_chart(fig_bubble, width="stretch")

    champions = cust[(cust["Orders"] >= med_orders) &
                     (cust["Avg order value"] >= med_aov)]["Customer ID"].tolist()
    st.markdown(
        f"**Takeaway:** {len(champions)} customer(s) buy often *and* spend above "
        f"the median per order: {', '.join(champions) or 'none'}. "
        f"These are the ones to protect with a loyalty offer."
    )

    st.divider()

    # ---------- Chart 2: Region → Customer sunburst ----------
    fig_sun = px.sunburst(
        df_f,
        path=["Region", "Customer ID"],
        values="Revenue",
        color="Region",
        color_discrete_sequence=px.colors.qualitative.Bold,
        title="Where does revenue come from? (click a region to zoom in)",
    )
    fig_sun.update_traces(
        textinfo="label+percent parent",
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>Revenue: £%{value:,.0f}"
                      "<br>Share of parent: %{percentParent:.0%}<extra></extra>",
    )
    fig_sun.update_layout(height=560, margin=dict(t=60, l=0, r=0, b=0))
    st.plotly_chart(fig_sun, width="stretch")

    st.caption("Inner ring = regions · outer ring = each customer's revenue "
               "within that region. Click the centre to zoom back out.")




with tab_data:
    st.dataframe(df_f, hide_index=True, width="stretch")
    st.download_button(
        "Download filtered data (CSV)",
        data=df_f.to_csv(index=False).encode("utf-8"),
        file_name="sales_filtered.csv",
        mime="text/csv",
    )

st.caption("Data: sales_data.csv (100 transactions, 2024).")
