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

st.title("🧾 Feilvarer")
st.caption("Registrer feil varer og marker som behandlet når saken er løst.")

WS = get_worksheet(
    st.secrets["gsheet"]["spreadsheet_url"],
    st.secrets["errors"]["worksheet"],  # e.g. "feilvarer"
)

EXPECTED_HEADERS = ["id", "dato", "varenummer", "navn", "antall_feil_varer", "status", "kommentar"]
STATUS_OPTIONS = ["Ny", "Under behandling", "Behandlet"]

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
def load_rows():
    ensure_headers()
    values = WS.get_all_values()
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    for col in ["id", "varenummer", "navn", "antall_feil_varer", "status", "kommentar"]:
        df[col] = df[col].fillna("").astype(str)

    df["dato"] = pd.to_datetime(df["dato"], errors="coerce").dt.date
    df["status"] = df["status"].apply(lambda s: s if s in STATUS_OPTIONS else "Ny")

    return df

def find_sheet_row_by_id(item_id: str) -> int | None:
    col = WS.col_values(1)  # id column
    for idx, val in enumerate(col[1:], start=2):
        if val == item_id:
            return idx
    return None

def add_error(dato_value: date, varenummer: str, navn: str, antall: int, status: str, kommentar: str):
    new_id = str(uuid.uuid4())
    WS.append_row([new_id, dato_value.isoformat(), varenummer, navn, str(antall), status, kommentar])

def set_status(item_id: str, new_status: str):
    row = find_sheet_row_by_id(item_id)
    if row is None:
        st.error("Fant ikke raden (kanskje slettet).")
        return
    WS.update(f"F{row}", [[new_status]])

def delete_item(item_id: str):
    row = find_sheet_row_by_id(item_id)
    if row is None:
        st.error("Fant ikke raden (kanskje slettet).")
        return
    WS.delete_rows(row)

# ---- ADD FORM ----
st.subheader("➕ Registrer feil vare")

with st.form("add_error_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([0.22, 0.25, 0.33, 0.20])
    with c1:
        dato_value = st.date_input("Dato *", value=date.today())
    with c2:
        varenummer = st.text_input("Varenummer *")
    with c3:
        navn = st.text_input("Navn *")
    with c4:
        antall = st.number_input("Antall *", min_value=1, step=1, value=1)

    status = st.selectbox("Status", STATUS_OPTIONS, index=0)
    kommentar = st.text_input("Kommentar", placeholder="Valgfritt")

    submitted = st.form_submit_button("Legg til", type="primary")
    if submitted:
        varenummer = varenummer.strip()
        navn = navn.strip()
        kommentar = kommentar.strip()
        if not varenummer or not navn:
            st.error("Varenummer og Navn er påkrevd.")
        else:
            add_error(dato_value, varenummer, navn, int(antall), status, kommentar)
            st.success("✅ Registrert!")
            st.cache_data.clear()
            st.rerun()

st.divider()

# ---- FILTERS ----
df = load_rows()

c1, c2 = st.columns([0.7, 0.3])
with c1:
    query = st.text_input("Søk", placeholder="Søk på varenummer / navn / kommentar…").strip().lower()
with c2:
    vis_behandlede = st.checkbox("Vis behandlede", value=False)

statuses = st.multiselect("Statusfilter", STATUS_OPTIONS, default=["Ny", "Under behandling"])

view = df.copy()

if not vis_behandlede:
    view = view[view["status"] != "Behandlet"]

if statuses:
    view = view[view["status"].isin(statuses)]

if query:
    view = view[
        view["varenummer"].str.lower().str.contains(query, na=False)
        | view["navn"].str.lower().str.contains(query, na=False)
        | view["kommentar"].str.lower().str.contains(query, na=False)
    ]

view = view.sort_values(by=["dato"], ascending=False)

st.subheader(f"📋 Oversikt ({len(view)} rader)")
show_cols = ["dato", "varenummer", "navn", "antall_feil_varer", "status", "kommentar"]
st.dataframe(view[show_cols], use_container_width=True)

st.divider()

# ---- ACTIONS (FILTER-FIRST) ----
st.subheader("⚡ Handlinger")

if view.empty:
    st.info("Ingen rader matcher filteret.")
else:
    N = st.slider("Antall rader i handlingslisten", 5, 100, 30)
    shortlist = view.head(N)

    options = []
    for _, r in shortlist.iterrows():
        label = f'{r["dato"]} | {r["varenummer"]} | {r["navn"]} | {r["status"]}'
        options.append((label, r["id"]))

    selected_label = st.selectbox("Velg rad (fra filtrert liste)", options=[o[0] for o in options])
    selected_id = dict(options)[selected_label]

    selected_row = df[df["id"] == selected_id].iloc[0]

    st.write(f"**Valgt:** {selected_row['varenummer']} — {selected_row['navn']}")
    st.write(f"Antall: {selected_row['antall_feil_varer']} | Status: {selected_row['status']}")
    if selected_row["kommentar"]:
        st.caption(selected_row["kommentar"])

    cA, cB, cC = st.columns(3)

    with cA:
        new_status = st.selectbox("Ny status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(selected_row["status"]))
        if st.button("Oppdater status", type="primary"):
            set_status(selected_id, new_status)
            st.cache_data.clear()
            st.rerun()

    with cB:
        if st.button("✅ Sett til Behandlet"):
            set_status(selected_id, "Behandlet")
            st.cache_data.clear()
            st.rerun()

    with cC:
        confirm_delete = st.checkbox("Bekreft sletting", value=False)
        if st.button("🗑️ Slett", disabled=not confirm_delete):
            delete_item(selected_id)
            st.cache_data.clear()
            st.rerun()
