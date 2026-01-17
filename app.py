"""
------------------------------------------------------------------------
Project: TS_XL_Modifier
Author:  Karl @ TechnoShed
Website: https://technoshed.co.uk
Repo:    https://github.com/TechnoShed-dev/TS_XL_Modifier

Description:
Streamlit web application for GBA VDAT imports.
Features:
- "Dashboard" Style UI
- Multi-sheet Excel/CSV parsing
- OCR / Camera Input for Paper Manifests (Tesseract)
- Automatic Brand/Model cleaning
- Deduplication
------------------------------------------------------------------------
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re
import os
from PIL import Image
import pytesseract

# --- App Configuration ---
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
    .css-10trblm { margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
col_logo, col_title = st.columns([1, 15])

with col_logo:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=100)
    else:
        st.write("⚙️")

with col_title:
    st.title("TS_XL_Modifier")

st.caption("Standardized VDAT Import Generator (Digital & OCR)")
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
    # Basic cleanup for OCR noise
    v = re.sub(r'[^A-Z0-9]', '', v) 
    
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

def extract_vins_from_image(image_file, default_brand, default_model):
    """
    Uses Tesseract OCR to read text from image, then Regex to find VINs.
    """
    image = Image.open(image_file)
    # Extract text
    text = pytesseract.image_to_string(image)
    
    # Regex for 17 char alphanumeric (excluding I, O, Q usually, but strict 17 is safer for OCR)
    # We allow some noise cleaning later
    potential_vins = re.findall(r'\b[A-HJ-NPR-Z0-9]{17}\b', text)
    
    data = []
    for vin in potential_vins:
        data.append({
            "VIN": vin,
            "BRAND": default_brand,
            "MODEL": default_model
        })
    
    return pd.DataFrame(data)

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

# --- TABS ---
tab1, tab2 = st.tabs(["📂 Excel/CSV Upload", "📷 Camera/OCR Scan"])

final_df = pd.DataFrame()
ocr_df = pd.DataFrame()
file_df = pd.DataFrame()

# =======================
# TAB 1: FILE UPLOAD
# =======================
with tab1:
    uploaded_file = st.file_uploader("Drop Shipping Line File", type=["xlsx", "xls", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                try: df_raw = pd.read_csv(uploaded_file, header=None)
                except: 
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=';', header=None)
                sheets = {"Sheet1": df_raw}
            else:
                sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
            
            all_clean_frames = []
            
            for sheet_name, df in sheets.items():
                if df.empty: continue
                try:
                    header_idx = find_header_row(df)
                    if header_idx is None: continue 
                    new_header = df.iloc[header_idx]
                    df_data = df.iloc[header_idx + 1:].copy()
                    df_data.columns = [f"{str(h).strip()}_{i}" for i, h in enumerate(new_header)]
                    
                    df_mapped = standardize_columns(df_data)
                    df_mapped["MODEL"] = df_mapped.apply(clean_model_name, axis=1)
                    
                    df_debug = df_mapped.copy()
                    df_debug["Status"], _ = zip(*df_debug["VIN"].apply(get_vin_status))
                    df_clean = df_debug[df_debug["Status"] == True].copy()
                    df_clean = df_clean[df_clean["BRAND"].astype(str).str.strip() != ""]
                    
                    if not df_clean.empty:
                        df_clean["BRAND"] = df_clean["BRAND"].apply(map_brand)
                        all_clean_frames.append(df_clean)
                except: continue

            if all_clean_frames:
                file_df = pd.concat(all_clean_frames, ignore_index=True)
                st.success(f"✅ Loaded {len(file_df)} vehicles from file.")
        except Exception as e:
            st.error(f"Error: {e}")

# =======================
# TAB 2: OCR SCANNER
# =======================
with tab2:
    st.markdown("### 📸 Scan Paper Manifests")
    st.info("Use this for KESS/HOD paper load sheets. Tesseract will scan for VINs.")
    
    oc1, oc2 = st.columns(2)
    with oc1:
        manual_brand = st.selectbox("Default Brand (for OCR)", ["OPEL", "VAUXHALL", "PEUGEOT", "CITROEN", "ASTON MARTIN"])
    with oc2:
        manual_model = st.text_input("Default Model (Optional)", value="")

    img_file = st.file_uploader("Upload Scan/Photo", type=["jpg", "png", "jpeg"])
    camera_file = st.camera_input("Or Take a Picture")
    
    target_img = camera_file if camera_file else img_file
    
    if target_img:
        st.image(target_img, caption="Scanning...", width=300)
        with st.spinner("Running OCR Engine..."):
            try:
                ocr_df = extract_vins_from_image(target_img, manual_brand, manual_model)
                if not ocr_df.empty:
                    st.success(f"✅ Found {len(ocr_df)} VINs in image!")
                    st.dataframe(ocr_df)
                else:
                    st.warning("⚠️ No 17-character VINs found. Try better lighting or crop closer.")
            except Exception as e:
                st.error(f"OCR Error: {e}")

# =======================
# MERGE & DOWNLOAD
# =======================
st.divider()

# Combine both sources
frames_to_merge = []
if not file_df.empty: frames_to_merge.append(file_df)
if not ocr_df.empty: frames_to_merge.append(ocr_df)

if frames_to_merge:
    final_df = pd.concat(frames_to_merge, ignore_index=True)
    
    # Deduplicate
    initial_count = len(final_df)
    final_df.drop_duplicates(subset=["VIN"], keep="first", inplace=True)
    dedup_count = initial_count - len(final_df)

    # VDAT Columns
    final_df["MODELTYPE"] = final_df["MODEL"]
    final_df["CUSTOMER"] = customer_code
    final_df["POA"] = poa_code
    final_df["DTMASSIGNEDDATE"] = datetime.now().strftime("%d/%m/%Y")
    
    cols = ["VIN", "BRAND", "MODEL", "MODELTYPE", "CUSTOMER", "POA", "DTMASSIGNEDDATE"]
    final_df = final_df[cols]
    
    # Download Logic
    output = io.BytesIO()
    clean_sheet_name = re.sub(r'[\\/*?:\[\]]', '', voyage_ref)[:31]
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False, sheet_name=clean_sheet_name)
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"VDAT_{customer_code}_{poa_code}_{timestamp}.xlsx"
    
    st.success(f"🎉 **Total Unique Vehicles:** {len(final_df)}")
    if dedup_count > 0: st.warning(f"Removed {dedup_count} duplicates.")
    
    st.download_button(
        label=f"⬇️ DOWNLOAD {fname}",
        data=output,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True
    )
else:
    st.info("👆 Upload a file or Scan an image to begin.")