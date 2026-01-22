import streamlit as st
import pandas as pd
from datetime import date
from gsheets import get_worksheet

def require_login():
    if not st.session_state.get("logged_in", False):
        st.warning("Please log in first.")
        st.stop()

require_login()

st.title("📦 Expiry products")
st.caption("Sorts by products that expire soon (dato).")

WS = get_worksheet(
    st.secrets["gsheet"]["spreadsheet_url"],
    st.secrets["expiry"]["worksheet"],  # "products"
)

@st.cache_data(ttl=20)
def load_products():
    values = WS.get_all_values()
    if not values:
        return pd.DataFrame(columns=["varenummer", "navn", "dato", "location"])

    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Parse date column (dato)
    df["dato"] = pd.to_datetime(df["dato"], errors="coerce").dt.date
    today = date.today()

    df["days_left"] = df["dato"].apply(
        lambda d: (d - today).days if pd.notna(d) else None
    )
    return df

days = st.slider("Show items expiring within (days)", 0, 365, 30)
show_expired = st.checkbox("Include already expired", value=True)

df = load_products()

filtered = df[df["dato"].notna()].copy()

if not show_expired:
    filtered = filtered[filtered["days_left"] >= 0]

filtered = filtered[filtered["days_left"] <= days]
filtered = filtered.sort_values("days_left", ascending=True)

def status(d):
    if d is None:
        return "Unknown"
    if d < 0:
        return "Expired"
    if d <= 7:
        return "Expiring soon"
    return "OK"

filtered["status"] = filtered["days_left"].apply(status)

st.dataframe(
    filtered[["varenummer", "navn", "dato", "days_left", "status", "location"]],
    use_container_width=True
)
