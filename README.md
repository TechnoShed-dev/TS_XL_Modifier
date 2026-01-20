# TS_XL_Modifier (TechnoShed)

**Version:** 2.10
**Live App:** [http://gba.technoshed.co.uk](http://gba.technoshed.co.uk)

A specialized Data Transformation Tool for GBA Group VDAT Imports.

---

## 📖 User Guide (How to Use)

### 1. Digital Files (Excel / CSV)
*Best for: Standard manifests from Stellantis (Grimaldi), Hoedlmayr, or KESS.*

1.  **Select Customer & POA:** Choose the correct Customer and Port of Arrival at the top.
2.  **Tab 1:** Select "📂 Excel/CSV Upload".
3.  **Upload:** Drag and drop your file.
4.  **Download:** Click the red **Download** button at the bottom.

### 2. Paper Sheets (Camera Scan)
*Best for: BCA / OnTime / Walon "Pulling Sheets" (Paper lists with tick marks).*

1.  **Tab 2:** Select "📷 Camera/OCR Scan".
2.  **Set Fallbacks:** Enter the Brand (e.g., `ASTON MARTIN`) if the paper doesn't say it.
3.  **Scan:** Click **"📸 Tap to use Webcam"**. Hold the paper flat.
    * *Note: The system automatically ignores red/blue/green pen marks.*
4.  **Review & Download:** Check the vehicle count and download the file.

### 3. Emails (Copy & Paste)
*Best for: Aston Martin truck requests or unstructured email lists.*

1.  **Tab 3:** Select "📋 Clipboard/Email".
2.  **Set Fallbacks:** Ensure Brand is set (e.g., `ASTON MARTIN`).
3.  **Paste:** Copy the entire email body and paste it into the box.
4.  **Process:** Click **Process Text**. The system will find the VINs automatically.

---

## 🛠 Technical Overview

TS_XL_Modifier is a lightweight, Dockerized web utility built to bridge the gap between raw Shipping Line Excel manifests and the internal GBA VDAT (Vehicle Data) AS/400 system. It serves as a "sanitation layer," accepting messy, multi-format Excel/CSV files, paper manifests (via OCR), or raw emails and outputting a strictly formatted import file.

### The Problem
Shipping lines (Stellantis, Hoedlmayr, INEOS, etc.) provide data that is often incompatible with VDAT import requirements:
* **Inconsistent Headers:** Columns vary between VIN, Chassis, Make, Brand, Model, OEM, etc.
* **Junk Data:** Files often contain Pivot Tables, summary rows, or multiple sheets.
* **Paper Manifests:** Some arrivals (e.g., KESS/HOD/OnTime) come with physical A4 load sheets covered in handwritten checks.
* **Unstructured Emails:** Truck requests often arrive as simple text lists in Outlook.

### Key Features

**1. Auto-Detect Headers:**
The "Header Hunter" algorithm scans every sheet to find the row containing VIN + context keywords, ignoring Pivot Table artifacts.

**2. Advanced OCR (Universal Ink Filter):**
* **Tesseract Engine:** Auto-extracts 17-digit VINs from images.
* **Ink Removal:** Uses custom Computer Vision (Max-Channel extraction) to erase red, blue, and green pen marks that cut through VINs.
* **Gamma Correction:** Automatically enhances contrast to read faded or gray text.

**3. Headless Email Parsing (New in v2.10):**
* Accepts raw copy-pasted text from Outlook.
* Detects VINs without headers using Regex pattern matching.
* Intelligently parses "VIN - Model - Dest" formats common in Aston Martin requests.

**4. Smart Normalization:**
* **Brand Mapping:** Converts Citroen -> CITR, Ineos -> INO, Peugeot -> PEUG.
* **Model Cleaning:** Strips brand names (`OPEL FRONTERA` -> `FRONTERA`) and prefixes.
* **Deduplication:** Ensures unique VINs across all inputs.

### Project Structure
* `app.py`: Main Application Logic (Streamlit)
* `Dockerfile`: Container definition (includes Tesseract)
* `docker-compose.yml`: Service orchestration
* `requirements.txt`: Python dependencies
* `logo.jpg`: TechnoShed Branding
* `README.md`: Documentation

### Quick Start (Docker)
```bash
docker-compose up -d --build
