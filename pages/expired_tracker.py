import streamlit as st
import pandas as pd
import uuid
from datetime import date
from gsheets import get_worksheet

def require_login():
    if not st.session_state.get("logged_in", False):
        st.warning("Vennligst logg inn først.")
        st.stop()

require_login()

st.title("📦 Holdbarhet")
st.caption("Sorterer varer etter utløpsdato (snart utløpt først).")

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
            "Feil i kolonneoverskrifter i Google Sheets.\n\n"
            f"Forventet: {EXPECTED_HEADERS}\n"
            f"Fant:      {headers}\n\n"
            "Fiks overskriftene i rad 1 slik at de matcher nøyaktig."
        )
        st.stop()

@st.cache_data(ttl=20)
def load_products():
    ensure_headers()
    values = WS.get_all_values()
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Make string columns safe for filtering
    for col in ["varenummer", "navn", "location"]:
        df[col] = df[col].fillna("").astype(str)

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
        st.error("Fant ikke varen i arket (kanskje den allerede er slettet).")
        return
    WS.delete_rows(row)

def delete_all_expired():
    """Delete all rows where dato < today (days_left < 0)."""
    values = WS.get_all_values()
    if not values or len(values) < 2:
        return 0

    headers = values[0]
    rows = values[1:]

    # Find relevant column indices
    try:
        id_idx = headers.index("id")
        dato_idx = headers.index("dato")
    except ValueError:
        st.error("Mangler kolonnene 'id' eller 'dato' i arket.")
        return 0

    today = date.today()

    # Determine sheet row numbers to delete (2..N)
    rows_to_delete = []
    for i, r in enumerate(rows, start=2):
        dato_str = r[dato_idx] if len(r) > dato_idx else ""
        d = pd.to_datetime(dato_str, errors="coerce").date() if dato_str else None
        if d is not None and (d - today).days < 0:
            rows_to_delete.append(i)

    # Delete from bottom to top to avoid shifting row numbers
    for row_number in reversed(rows_to_delete):
        WS.delete_rows(row_number)

    return len(rows_to_delete)

# ---- ADD PRODUCT ----
st.subheader("➕ Legg til vare")

with st.form("add_product_form", clear_on_submit=True):
    varenummer = st.text_input("Varenummer *")
    navn = st.text_input("Navn *")
    dato_value = st.date_input("Utløpsdato *", value=date.today())
    location = st.text_input("Plassering")
    submitted = st.form_submit_button("Legg til", type="primary")

    if submitted:
        varenummer = varenummer.strip()
        navn = navn.strip()
        location = location.strip()

        if not varenummer or not navn:
            st.error("Fyll inn feltene merket med * (Varenummer og Navn).")
        else:
            add_product_to_sheet(varenummer, navn, dato_value, location)
            st.success("✅ Vare lagt til!")
            st.cache_data.clear()
            st.rerun()

st.divider()

# ---- FILTERS ----
df = load_products()

search = st.text_input("Søk (varenummer/navn/plassering)", placeholder="Skriv for å filtrere…").strip().lower()
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
        return "Ukjent"
    if d < 0:
        return "Utløpt"
    if d <= 30:
        return "Utløper snart"
    return "OK"

filtered["status"] = filtered["days_left"].apply(status)

# ---- BULK DELETE EXPIRED ----
st.subheader("🧹 Rydding")

confirm_delete = st.checkbox("Jeg forstår at sletting er permanent", value=False)
confirm_bulk = st.checkbox("Bekreft: Slett ALLE utløpte varer", value=False)

c1, c2 = st.columns([0.7, 0.3])
with c1:
    st.write("Slett alle varer som allerede er utløpt (dato før i dag).")
with c2:
    if st.button("🧹 Slett alle utløpte", disabled=not (confirm_delete and confirm_bulk)):
        deleted = delete_all_expired()
        st.success(f"🧹 Slettet {deleted} utløpte varer.")
        st.cache_data.clear()
        st.rerun()

st.divider()

# ---- PRODUCTS LIST WITH DELETE ----
st.subheader("📋 Produkter (sortert etter nærmeste utløpsdato)")

if filtered.empty:
    st.info("Ingen varer matcher filteret.")
else:
    for _, row in filtered.iterrows():
        # background highlight
        bg = ""
        if row["days_left"] is not None:
            if row["days_left"] < 0:
                bg = "rgba(255, 0, 0, 0.10)"
            elif row["days_left"] <= 7:
                bg = "rgba(255, 255, 0, 0.15)"

        c1, c2 = st.columns([0.85, 0.15])

        with c1:
            st.markdown(
                f"""
                <div style="
                    background-color:{bg};
                    padding:10px;
                    border-radius:6px;
                    margin-bottom:6px;">
                    <b>{row['varenummer']}</b> — {row['navn']}<br>
                    📅 {row['dato']} &nbsp;&nbsp; ⏳ {row['days_left']} dager igjen &nbsp;&nbsp; ({row['status']})<br>
                    📍 {row['location']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c2:
            if st.button("🗑️ Slett", key=f"del_{row['id']}", disabled=not confirm_delete):
                delete_by_id(row["id"])
                st.success("🗑️ Vare slettet")
                st.cache_data.clear()
                st.rerun()

if not confirm_delete:
    st.caption("Tips: Huk av «Jeg forstår at sletting er permanent» for å aktivere Slett-knappene.")
