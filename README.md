# 🌾 Krishi Khoj — Turn Farm PDFs into Searchable Data

**Track:** Bhoomi & Bharosa Bharat  
**Theme:** Farmers, Land and the Data Commons  
**Problem Statement:** PS 3.4  

---

## 🎯 What is Krishi Khoj?

Official farming advice is often locked inside PDF circulars, advisories, and package of practices documents that are hard to search, compare, or verify. When facts are copied out manually, errors are difficult to detect without referring back to the original source page and document version.

**Krishi Khoj** extracts existing facts from farming advisory PDFs into structured, queryable data fields while preserving a verifiable provenance link (SHA-256 hash, version number, page number, and original context snippet) for every fact.

> ⚠️ **Core Principle:** Krishi Khoj **extracts and organizes existing official facts**; it **never generates or hallucinates new advice**.

---

## 🚀 How to Run the App

### Option 1: Quick Start (Single Command)

Open your terminal, navigate to the folder, and run:

```bash
cd "/Users/anubhav/Downloads/Krishi Khoj"
./run.sh
```

*(This automatically creates `.venv`, installs requirements, generates sample PDFs, and starts the server).*

---

### Option 2: Step-by-Step Manual Setup

1. **Navigate to the project folder:**
   ```bash
   cd "/Users/anubhav/Downloads/Krishi Khoj"
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Generate sample advisory PDFs for testing:**
   ```bash
   python3 sample_pdfs/generate_sample.py
   ```
   *Generates realistic advisory PDFs for Wheat and Rice in `sample_pdfs/`.*

5. **Run the Flask application:**
   ```bash
   python3 app.py
   ```

6. **Open in your browser:**
   ```
   http://127.0.0.1:5000
   ```

---

## 🧪 Testing with Sample PDFs

Two realistic Indian agricultural advisory PDFs are included or can be generated via `sample_pdfs/generate_sample.py`:
- `Wheat_Cultivation_Guide_2024.pdf`: Covers varieties (HD-2967, PBW-343), soil pH (6.0-7.5), seed rates (100 kg/ha), NPK fertilizer doses (120:60:40 kg/ha), 6 critical irrigation stages, yellow rust remedies, and expected yields (45-50 q/ha).
- `Rice_Production_Technology_2024.pdf`: Covers Kharif rice, SRI seed rate (5-7 kg/ha), NPK fertilizer splits, pest management (Cartap for stem borer, Imidacloprid for BPH), and yields (55-65 q/ha).

Upload either of these from the home page to immediately see facts categorized and linked to their original source pages!

---

## 💡 Key Features

| Feature | Description |
|---|---|
| **Tamper-Evident Provenance** | Computes SHA-256 checksum for every PDF; detects re-uploads and versions documents automatically. |
| **Page-Level Granularity** | Every extracted fact records its exact page number and raw surrounding sentence. |
| **8 Structured Categories** | Organizes facts into **Fertilizer**, **Seed**, **Irrigation**, **Pest**, **Soil**, **Yield**, **Season**, and **General**. |
| **Value & Unit Extraction** | Identifies numeric rates and units (e.g. `120 kg/ha`, `2.5 g/kg`, `5-6 irrigations`). |
| **Interactive Search & Filter** | Filter facts by crop, category, season, or keyword; keyboard shortcut (`/`) focuses search. |
| **Source Context Viewer** | View the complete raw text of the source page with the extracted fact highlighted in yellow. |
| **Data Commons Export** | Download filtered or complete fact sets in **CSV** or **JSON** for downstream research and tools. |

---

## 📡 API Endpoints

- `GET /api/search?q=fertilizer&crop=Wheat&category=Fertilizer`: Search facts with filters
- `GET /api/stats`: Dashboard counts (documents, facts, categories, crops)
- `GET /api/documents`: List of documents with checksums & page counts
- `GET /api/export?format=csv`: Export facts to CSV
- `GET /api/export?format=json`: Export facts to JSON

