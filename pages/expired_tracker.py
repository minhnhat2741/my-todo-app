import streamlit as st
import pandas as pd
import uuid
from datetime import date
from gsheets import get_worksheet

def require_login():
    if not st.session_state.get("logged_in", False):
        st.warning("Please log in first.")
        st.stop()

require_login()

st.title("📦 Holdbarhet")
st.caption("Sortert etter utløpsdato.")

WS = get_worksheet(
    st.secrets["gsheet"]["spreadsheet_url"],
    st.secrets["expiry"]["worksheet"],  # e.g. "products"
)

EXPECTED_HEADERS = ["id", "varenummer", "navn", "dato", "location"]

def ensure_headers():
    values = WS.get_all_values()
    if not values:
        WS.append_row(EXPECTED_HEADERS)
        return

    headers = values[0]
    if headers != EXPECTED_HEADERS:
        st.error(
            "Header mismatch in products sheet.\n\n"
            f"Expected: {EXPECTED_HEADERS}\n"
            f"Found:    {headers}\n\n"
            "Fix the headers in Google Sheets (row 1) to match exactly."
        )
        st.stop()

@st.cache_data(ttl=20)
def load_products():
    ensure_headers()
    values = WS.get_all_values()
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

def add_product_to_sheet(varenummer: str, navn: str, dato_value: date, location: str):
    new_id = str(uuid.uuid4())
    WS.append_row([new_id, varenummer, navn, dato_value.isoformat(), location])

def find_row_by_id(item_id: str) -> int | None:
    """Return sheet row number (1-indexed) for given id, or None."""
    col = WS.col_values(1)  # column A = id, includes header
    for idx, val in enumerate(col[1:], start=2):
        if val == item_id:
            return idx
    return None

def delete_by_id(item_id: str):
    row = find_row_by_id(item_id)
    if row is None:
        st.error("Could not find the item in the sheet (maybe already deleted).")
        return
    WS.delete_rows(row)

def update_by_id(item_id: str, varenummer: str, navn: str, dato_value: date, location: str):
    row = find_row_by_id(item_id)
    if row is None:
        st.error("Could not find the item in the sheet (maybe deleted).")
        return
    # Update columns B..E (varenummer, navn, dato, location)
    WS.update(f"B{row}:E{row}", [[varenummer, navn, dato_value.isoformat(), location]])

# ---- ADD PRODUCT ----
st.subheader("➕ Add product")

with st.form("add_product_form", clear_on_submit=True):
    varenummer = st.text_input("Varenummer *")
    navn = st.text_input("Navn *")
    dato_value = st.date_input("Dato (utløpsdato) *", value=date.today())
    location = st.text_input("Location")
    submitted = st.form_submit_button("Add", type="primary")

    if submitted:
        varenummer = varenummer.strip()
        navn = navn.strip()
        location = location.strip()

        if not varenummer or not navn:
            st.error("Please fill in required fields: Varenummer and Navn.")
        else:
            add_product_to_sheet(varenummer, navn, dato_value, location)
            st.success("✅ Product added!")
            st.cache_data.clear()
            st.rerun()

st.divider()

# ---- FILTERS ----
df = load_products()

search = st.text_input("Søk (varenummer/navn/location)", placeholder="Type to filter…").strip().lower()
days = st.slider("Vis varer som utløper innen (dager)", 0, 365, 30)
show_expired = st.checkbox("Inkluder allerede utløpte varer", value=True)

filtered = df.copy()
filtered = filtered[filtered["dato"].notna()]  # keep only valid dates

if search:
    filtered = filtered[
        filtered["varenummer"].str.lower().str.contains(search, na=False)
        | filtered["navn"].str.lower().str.contains(search, na=False)
        | filtered["location"].str.lower().str.contains(search, na=False)
    ]

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

# ---- HIGHLIGHT TABLE ----
st.subheader("📋 Produkter (sortert etter nærmeste utløpsdato)")

def highlight_row(row):
    d = row.get("days_left")
    if d is None:
        return [""] * len(row)
    if d < 0:
        return ["background-color: rgba(255, 0, 0, 0.15)"] * len(row)
    if d <= 7:
        return ["background-color: rgba(255, 255, 0, 0.15)"] * len(row)
    return [""] * len(row)

show_cols = ["varenummer", "navn", "dato", "days_left", "status", "location"]
styled = filtered[show_cols].style.apply(highlight_row, axis=1)
st.dataframe(styled, use_container_width=True)

st.divider()

# ---- EDIT / DELETE ----
st.subheader("✏️ Edit or 🗑️ Delete")

if filtered.empty:
    st.info("No products match your filter.")
else:
    options = []
    for _, r in filtered.iterrows():
        label = f'{r["varenummer"]} — {r["navn"]} — {r["dato"]} — {r["location"]}'
        options.append((label, r["id"]))

    selected_label = st.selectbox(
        "Select product",
        options=[o[0] for o in options],
    )
    selected_id = dict(options)[selected_label]

    # Get the row data from full df (not only filtered)
    row_data = df[df["id"] == selected_id].iloc[0]

    with st.form("edit_form"):
        new_varenummer = st.text_input("Varenummer", value=str(row_data["varenummer"]))
        new_navn = st.text_input("Navn", value=str(row_data["navn"]))
        new_dato = st.date_input("Dato", value=row_data["dato"] if pd.notna(row_data["dato"]) else date.today())
        new_location = st.text_input("Location", value=str(row_data["location"]))

        c1, c2 = st.columns(2)
        with c1:
            save = st.form_submit_button("Save changes", type="primary")
        with c2:
            delete = st.form_submit_button("Delete", help="Deletes this product from the sheet")

        if save:
            update_by_id(selected_id, new_varenummer.strip(), new_navn.strip(), new_dato, new_location.strip())
            st.success("✅ Updated!")
            st.cache_data.clear()
            st.rerun()

        if delete:
            delete_by_id(selected_id)
            st.success("🗑️ Deleted!")
            st.cache_data.clear()
            st.rerun()
