"""
------------------------------------------------------------------------
Project: TS_XL_Modifier
Author:  Karl @ TechnoShed
Website: https://technoshed.co.uk
Repo:    https://github.com/TechnoShed-dev/TS_XL_Modifier

Description:
Streamlit web application for GBA VDAT imports.
Features:
- Multi-sheet parsing
- Robust error handling (skips bad sheets)
- "Voyage Ref" input for Sheet Name (Field1 tracking)
- Automatic Brand/Model cleaning
- DEDUPLICATION: Removes duplicate VINs and rows with missing Brands.
------------------------------------------------------------------------
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# --- App Configuration ---
st.set_page_config(page_title="TS_XL_Modifier", layout="wide")

st.markdown("""
<style>
    .stFileUploader > div > div {
        border: 2px dashed #4CAF50;
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
    }
    .sheet-error { border: 1px solid red; padding: 10px; border-radius: 5px; background-color: #ffe6e6; }
</style>
""", unsafe_allow_html=True)

st.title("🚜 TS_XL_Modifier")
st.caption("Standardized VDAT Import Generator with Data Inspector")
st.markdown("---")

# --- LOOKUP TABLES ---

CUSTOMER_MAP = {
    "Hoedlmayr": "HOD",
    "Stellantis": "STS",
    "INEOS": "INO",
    "Aston Martin Lagonda": "AML",
    "Bentley Motors Ltd": "BML",
    "KESS Groning": "KGR",
    "Neptune JLR": "LRE"
}

POA_MAP = {
    "Grimsby": "GRIM",
    "Zeebrugge": "ZEEB",
    "Malmo": "MALM",
    "Emden": "EMD",
    "Setubal": "SETU"
}

BRAND_TO_CODE = {
    "OPEL": "OPEL",
    "CITROEN": "CITR",
    "CITR": "CITR",
    "PEUGEOT": "PEUG",
    "PEUG": "PEUG",
    "INEOS": "INO",
    "ASTON MARTIN": "AML",
    "BENTLEY": "BML",
    "JAGUAR LANDROVER": "JLR",
    "JLR": "JLR",
    "FIAT": "FIAT",
    "JEEP": "JEEP"
}

# --- HELPER FUNCTIONS ---

def get_vin_status(vin_raw):
    if pd.isna(vin_raw): return False, "Empty/NaN"
    v = str(vin_raw).strip().upper()
    if len(v) != 17: return False, f"Invalid Length ({len(v)})"
    if not v[-6:].isdigit(): return False, f"Suffix Not Numeric ({v[-6:]})"
    return True, "OK"

def map_brand(raw_brand):
    if pd.isna(raw_brand): return ""
    b = str(raw_brand).strip().upper()
    if b in BRAND_TO_CODE: return BRAND_TO_CODE[b]
    for key, code in BRAND_TO_CODE.items():
        if key in b: return code
    return b

def clean_model_name(row):
    brand_code = map_brand(row.get("BRAND", ""))
    raw_brand_name = str(row.get("BRAND", "")).strip().upper()
    model_raw = str(row.get("MODEL", "")).strip().upper()
    
    if not model_raw: return ""

    # Rule 1: Remove Full Brand Name
    if raw_brand_name and model_raw.startswith(raw_brand_name):
        return model_raw[len(raw_brand_name):].strip()

    # Rule 2: Remove Single Letter Manufacturer Prefixes
    prefix_map = {"PEUG": "P", "CITR": "C", "OPEL": "O", "FIAT": "F"}
    if brand_code in prefix_map:
        prefix = prefix_map[brand_code]
        if model_raw.startswith(prefix):
             stripped = model_raw[1:].strip()
             if stripped: return stripped
    return model_raw

def find_header_row(df, scan_limit=50):
    for i in range(min(scan_limit, len(df))):
        row_values = [str(val).strip().upper() for val in df.iloc[i].tolist()]
        
        has_vin = any("VIN" == col or "VIN" in col for col in row_values)
        if any("COUNT OF" in col for col in row_values): continue # Pivot guard

        if has_vin:
            has_context = any(k in val for val in row_values for k in ["MAKE", "BRAND", "MODEL", "MAKER", "OEM", "COMMODITY", "CUST", "DESTINATION"])
            if has_context: return i
    return None

def standardize_columns(df):
    col_map = {}
    cols = df.columns
    
    # 1. Find VIN
    for c in cols:
        c_up = str(c).upper().strip()
        if "VIN" in c_up:
            col_map[c] = "VIN"
            break 

    # 2. Find BRAND
    for c in cols:
        c_up = str(c).upper().strip()
        if c not in col_map and any(k in c_up for k in ["MAKE", "BRAND", "OEM", "MAKER"]):
            col_map[c] = "BRAND"
            break 

    # 3. Find MODEL
    for c in cols:
        c_up = str(c).upper().strip()
        if c not in col_map and "MODEL" in c_up:
            col_map[c] = "MODEL"
            break 

    df = df.rename(columns=col_map)
    for req in ["VIN", "BRAND", "MODEL"]:
        if req not in df.columns: df[req] = ""
    
    return df.loc[:, ~df.columns.duplicated()][["VIN", "BRAND", "MODEL"]]

# --- UI SECTION ---

with st.container():
    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1])
    
    with c1:
        cust_key = st.selectbox("Customer", list(CUSTOMER_MAP.keys()))
        customer_code = CUSTOMER_MAP[cust_key]
        
    with c2:
        poa_key = st.selectbox("POA", list(POA_MAP.keys()))
        poa_code = POA_MAP[poa_key]
        
    with c3:
        default_batch = f"{datetime.now().strftime('%d%m%Y')}{customer_code}"
        voyage_ref = st.text_input("Voyage / Batch Ref", value=default_batch, help="This sets the Excel Sheet Name for VMS tracking.")
        
    with c4:
        st.write("") 
        st.info(f"Sheet Name: **{voyage_ref}**")

uploaded_file = st.file_uploader("Drop Shipping Line File", type=["xlsx", "xls", "csv"])

# --- PROCESSOR ---

if uploaded_file:
    st.divider()
    
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            try:
                df_raw = pd.read_csv(uploaded_file, header=None)
            except:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, sep=';', header=None)
            sheets = {"Sheet1": df_raw}
        else:
            sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    except Exception as e:
        st.error(f"❌ Critical Error Loading File: {e}")
        st.stop()

    all_clean_frames = []
    
    st.write(f"📂 Found {len(sheets)} sheet(s). Processing...")

    for sheet_name, df in sheets.items():
        if df.empty: continue
        
        try:
            with st.expander(f"Sheet: {sheet_name}", expanded=True):
                header_idx = find_header_row(df)
                if header_idx is None:
                    st.warning("⚠️ Ignored: No Header Row Found")
                    continue 

                new_header = df.iloc[header_idx]
                df_data = df.iloc[header_idx + 1:].copy()
                df_data.columns = [f"{str(h).strip()}_{i}" for i, h in enumerate(new_header)]
                
                df_mapped = standardize_columns(df_data)
                df_mapped["MODEL"] = df_mapped.apply(clean_model_name, axis=1)

                df_debug = df_mapped.copy()
                df_debug["Status"], df_debug["Reason"] = zip(*df_debug["VIN"].apply(get_vin_status))
                
                # PRE-FILTER: Flag rows with MISSING BRAND
                def check_brand(row):
                    if not row["BRAND"] or pd.isna(row["BRAND"]) or str(row["BRAND"]).strip() == "":
                        return False, "Missing Brand"
                    return row["Status"], row["Reason"]

                # Re-evaluate status based on Brand existence
                for idx, row in df_debug.iterrows():
                    if row["Status"]: # Only re-check if VIN is okay
                        status, reason = check_brand(row)
                        df_debug.at[idx, "Status"] = status
                        df_debug.at[idx, "Reason"] = reason

                def color_status(val):
                    color = '#d4edda' if val == 'OK' else '#f8d7da'
                    return f'background-color: {color}'

                st.write(f"**Found Data (Header at Row {header_idx+1}):**")
                st.dataframe(df_debug.head(10).style.applymap(color_status, subset=['Reason']))

                df_clean = df_debug[df_debug["Status"] == True].copy()
                
                if not df_clean.empty:
                    df_clean["BRAND"] = df_clean["BRAND"].apply(map_brand)
                    all_clean_frames.append(df_clean)
                    st.success(f"✅ Extracted {len(df_clean)} valid vehicles.")
                else:
                    st.error("❌ No valid vehicles (VINs invalid or Brand missing).")

        except Exception as e:
            st.markdown(f"<div class='sheet-error'><b>❌ Crash in Sheet '{sheet_name}':</b><br>{str(e)}</div>", unsafe_allow_html=True)

    # --- FINAL MERGE ---
    if all_clean_frames:
        final_df = pd.concat(all_clean_frames, ignore_index=True)
        
        # --- DEDUPLICATION ---
        # If a VIN appears twice, keep the first one found.
        initial_count = len(final_df)
        final_df.drop_duplicates(subset=["VIN"], keep="first", inplace=True)
        final_count = len(final_df)
        
        if initial_count > final_count:
            st.warning(f"⚠️ Removed {initial_count - final_count} duplicate VINs found across sheets.")

        final_df["MODELTYPE"] = final_df["MODEL"]
        final_df["CUSTOMER"] = customer_code
        final_df["POA"] = poa_code
        final_df["DTMASSIGNEDDATE"] = datetime.now().strftime("%d/%m/%Y")
        
        cols = ["VIN", "BRAND", "MODEL", "MODELTYPE", "CUSTOMER", "POA", "DTMASSIGNEDDATE"]
        final_df = final_df[cols]
        
        st.divider()
        st.success(f"🎉 Processing Complete! Total: {len(final_df)} Unique Vehicles")
        
        output = io.BytesIO()
        clean_sheet_name = re.sub(r'[\\/*?:\[\]]', '', voyage_ref)[:31]
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name=clean_sheet_name)
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"VDAT_{customer_code}_{poa_code}_{timestamp}.xlsx"
        
        st.download_button(
            label=f"⬇️ Download {fname}",
            data=output,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.warning("⚠️ No valid data found in any sheet.")