"""
------------------------------------------------------------------------
Project: TS_XL_Modifier
Author:  Karl @ TechnoShed
Website: https://technoshed.co.uk
Repo:    https://github.com/TechnoShed-dev/TS_XL_Modifier

Description:
Streamlit web application for GBA VDAT imports.
Features:
- Professional Header with Logo
- "Dashboard" Style Layout
- Multi-sheet parsing with Pivot Table detection
- Automatic Brand/Model cleaning (Prefix removal)
- Deduplication of VINs
- "Voyage Ref" input for Excel Sheet Naming
------------------------------------------------------------------------
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import os

# --- App Configuration ---
# You can set the browser tab icon here (I set it to 'favicon' style)
st.set_page_config(page_title="TS_XL_Modifier", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
    .stFileUploader > div > div {
        border: 2px dashed #4CAF50;
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .big-font { font-size:20px !important; font-weight: bold; }
    
    /* Vertical align the title to match the logo better */
    .css-10trblm { 
        margin-top: 20px; 
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION (Logo + Title) ---
# Create two columns: Narrow one for Logo, Wide one for Title
col_logo, col_title = st.columns([1, 15]) # 1:15 ratio keeps logo tight to left

with col_logo:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=100) # Nice and small
    else:
        st.write("⚙️") # Fallback if image missing

with col_title:
    # Removed the Tractor emoji
    st.title("TS_XL_Modifier")

st.caption("Standardized VDAT Import Generator")
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
    
    if raw_brand_name and model_raw.startswith(raw_brand_name):
        return model_raw[len(raw_brand_name):].strip()
        
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
        if any("COUNT OF" in col for col in row_values): continue 
        if has_vin:
            has_context = any(k in val for val in row_values for k in ["MAKE", "BRAND", "MODEL", "MAKER", "OEM", "COMMODITY", "CUST", "DESTINATION"])
            if has_context: return i
    return None

def standardize_columns(df):
    col_map = {}
    cols = df.columns
    for c in cols:
        c_up = str(c).upper().strip()
        if "VIN" in c_up:
            col_map[c] = "VIN"
            break 
    for c in cols:
        c_up = str(c).upper().strip()
        if c not in col_map and any(k in c_up for k in ["MAKE", "BRAND", "OEM", "MAKER"]):
            col_map[c] = "BRAND"
            break 
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

c1, c2, c3, c4 = st.columns([1, 1, 1.5, 1])
with c1:
    cust_key = st.selectbox("Customer", list(CUSTOMER_MAP.keys()))
    customer_code = CUSTOMER_MAP[cust_key]
with c2:
    poa_key = st.selectbox("POA", list(POA_MAP.keys()))
    poa_code = POA_MAP[poa_key]
with c3:
    default_batch = f"{datetime.now().strftime('%d%m%Y')}{customer_code}"
    voyage_ref = st.text_input("Voyage / Batch Ref", value=default_batch)
with c4:
    st.write("") 
    st.info(f"Ref: **{voyage_ref}**")

uploaded_file = st.file_uploader("Drop Shipping Line File", type=["xlsx", "xls", "csv"])

download_container = st.container()
summary_container = st.container()

# --- PROCESSING ---

if uploaded_file:
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
        st.error(f"❌ Critical Error: {e}")
        st.stop()

    all_clean_frames = []
    sheet_summary = [] 

    with st.spinner("Processing Sheets..."):
        for sheet_name, df in sheets.items():
            if df.empty: continue
            
            try:
                header_idx = find_header_row(df)
                if header_idx is None:
                    sheet_summary.append({"Sheet": sheet_name, "Vehicles": 0, "Status": "⚠️ Ignored (No Header)"})
                    continue 

                new_header = df.iloc[header_idx]
                df_data = df.iloc[header_idx + 1:].copy()
                df_data.columns = [f"{str(h).strip()}_{i}" for i, h in enumerate(new_header)]
                
                df_mapped = standardize_columns(df_data)
                df_mapped["MODEL"] = df_mapped.apply(clean_model_name, axis=1)

                df_debug = df_mapped.copy()
                df_debug["Status"], _ = zip(*df_debug["VIN"].apply(get_vin_status))
                
                df_clean = df_debug[df_debug["Status"] == True].copy()
                df_clean = df_clean[df_clean["BRAND"].astype(str).str.strip() != ""]
                
                count = len(df_clean)
                
                if count > 0:
                    df_clean["BRAND"] = df_clean["BRAND"].apply(map_brand)
                    all_clean_frames.append(df_clean)
                    sheet_summary.append({"Sheet": sheet_name, "Vehicles": count, "Status": "✅ OK"})
                else:
                    sheet_summary.append({"Sheet": sheet_name, "Vehicles": 0, "Status": "❌ No valid data"})

            except Exception as e:
                sheet_summary.append({"Sheet": sheet_name, "Vehicles": 0, "Status": f"🔥 Error: {str(e)}"})

    if all_clean_frames:
        final_df = pd.concat(all_clean_frames, ignore_index=True)
        
        initial_count = len(final_df)
        final_df.drop_duplicates(subset=["VIN"], keep="first", inplace=True)
        final_count = len(final_df)
        dedup_count = initial_count - final_count

        final_df["MODELTYPE"] = final_df["MODEL"]
        final_df["CUSTOMER"] = customer_code
        final_df["POA"] = poa_code
        final_df["DTMASSIGNEDDATE"] = datetime.now().strftime("%d/%m/%Y")
        
        cols = ["VIN", "BRAND", "MODEL", "MODELTYPE", "CUSTOMER", "POA", "DTMASSIGNEDDATE"]
        final_df = final_df[cols]
        
        with download_container:
            output = io.BytesIO()
            clean_sheet_name = re.sub(r'[\\/*?:\[\]]', '', voyage_ref)[:31]
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, sheet_name=clean_sheet_name)
            output.seek(0)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            fname = f"VDAT_{customer_code}_{poa_code}_{timestamp}.xlsx"
            
            st.success(f"🎉 **Success!** Prepared {len(final_df)} unique vehicles.")
            st.download_button(
                label=f"⬇️ DOWNLOAD {fname}",
                data=output,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

        with summary_container:
            st.markdown("### 📊 Processing Summary")
            st.table(pd.DataFrame(sheet_summary))
            
            if dedup_count > 0:
                st.warning(f"⚠️ Removed {dedup_count} duplicate VINs found across sheets.")

    else:
        with download_container:
            st.error("❌ No valid vehicle data found in any sheet.")
        with summary_container:
             st.table(pd.DataFrame(sheet_summary))