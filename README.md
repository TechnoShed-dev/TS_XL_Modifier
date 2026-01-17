# TS_XL_Modifier (TechnoShed)

A specialized Data Transformation Tool for GBA Group VDAT Imports.

## Overview
TS_XL_Modifier is a lightweight, Dockerized web utility built to bridge the gap between raw Shipping Line Excel manifests and the internal GBA VDAT (Vehicle Data) AS/400 system.

It serves as a "sanitation layer," accepting messy, multi-format Excel/CSV files and outputting a strictly formatted, clean import file ready for the VMS Importer.

## The Problem
Shipping lines (Stellantis, Hoedlmayr, INEOS, etc.) provide data that is often incompatible with VDAT import requirements:
* Inconsistent Headers: Columns vary between VIN, Chassis, Make, Brand, Model, OEM, etc.
* Junk Data: Files often contain Pivot Tables, summary rows, or multiple sheets with partial data.
* Redundant Naming: Models often include the brand name (e.g., INEOS GRENADIER).
* Legacy Prefixes: Manufacturer internal codes often intrude (e.g., P208 for Peugeot 208, CC3 for Citroen C3).
* Duplicates: The same VIN often appears in multiple sheets or status updates.

## Key Features
1. Auto-Detect Headers:
   The "Header Hunter" algorithm scans every sheet to find the row containing VIN + context keywords, ignoring Pivot Table artifacts.

2. Smart Normalization:
   * Brand Mapping: Converts Citroen -> CITR, Ineos -> INO, Peugeot -> PEUG (Standard VDAT Codes).
   * Model Cleaning: Strips brand names (OPEL FRONTERA -> FRONTERA) and legacy prefixes (P208 -> 208).

3. Deduplication:
   Ensures unique VINs across all sheets. Prioritizes valid records over records with missing Brands.

4. Voyage / Batch Tracking:
   Allows the user to define a "Voyage Ref" (e.g., 17012026HOD). This is written as the Excel Sheet Name in the output, which VMS uses to tag the import batch (Field1).

5. Dashboard UI:
   Clean, "At-a-glance" summary of processed sheets and valid vehicle counts.

## Quick Start (Docker)

1. Build & Run
   docker-compose up -d --build

2. Access the App
   Open your browser to: http://localhost:8501

3. Usage Steps
   * Select Context: Choose the Customer (e.g., Hoedlmayr) and Port of Arrival (e.g., Grimsby).
   * Set Batch Ref: Enter the Voyage Number or Batch ID (Defaults to Date+Customer).
   * Upload: Drag & drop your Excel or CSV file.
   * Download: Click the large green download button to get the VDAT_Import.xlsx file.

## Project Structure
* app.py: Main Application Logic (Streamlit)
* Dockerfile: Container definition
* docker-compose.yml: Service orchestration
* requirements.txt: Python dependencies
* logo.jpg: TechnoShed Branding
* README.md: Documentation

## License
Internal Use Only - GBA Group / TechnoShed Dev.
Developed by Karl.