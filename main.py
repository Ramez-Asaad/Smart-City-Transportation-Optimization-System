import os
import sys
from pathlib import Path
import streamlit as st

# Add the project root directory to Python path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# Verify data directory exists
data_dir = project_root / "data"
if not data_dir.exists():
    st.error("Data directory not found. Please ensure the 'data' directory exists in the project root.")
    st.stop()

# Verify required data files exist
required_files = [
    "neighborhoods.csv",
    "roads.csv",
    "facilities.csv",
    "bus_routes.csv",
    "metro_lines.csv",
    "demand_data.csv"
]

missing_files = []
for file in required_files:
    if not (data_dir / file).exists():
        missing_files.append(file)

if missing_files:
    st.error(f"Missing required data files: {', '.join(missing_files)}")
    st.error("Please ensure all required data files are present in the 'data' directory.")
    st.stop()

# Import app only after verifying data files
from UI.app import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("If this error persists, please check the data files and try again.")
