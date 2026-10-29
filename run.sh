#!/usr/bin/env bash
# 🌾 Krishi Khoj — Startup Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🌾 Krishi Khoj — Turn Farm PDFs into Searchable Data"
echo "=========================================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not found."
    exit 1
fi

# 2. Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# 3. Install Dependencies
echo "📥 Checking & installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 4. Generate Sample PDFs (if not already generated)
if [ ! -f "sample_pdfs/Wheat_Cultivation_Guide_2024.pdf" ]; then
    echo "📄 Generating sample farming advisory PDFs for testing..."
    python3 sample_pdfs/generate_sample.py
fi

# 5. Launch Application
echo "=========================================================="
echo "🚀 Starting Krishi Khoj at: http://127.0.0.1:5000"
echo "   Press Ctrl+C to stop the server"
echo "=========================================================="
python3 app.py

