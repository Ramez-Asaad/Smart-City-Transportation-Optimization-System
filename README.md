#CItyWise : A Smart City Transportation Optimization System

**CityWise**: A Streamlit-powered platform for urban mobility analytics, route planning, and public transit optimization in smart cities.

---

## Overview

CityWise is an interactive web application designed to optimize urban transportation networks. It provides advanced route planning for both public transit and private vehicles, dynamic schedule optimization, real-time network analytics, and comprehensive infrastructure reports. The system leverages modern algorithms (Dijkstra, A*, Minimum Spanning Tree, Dynamic Programming) and rich visualizations to support city planners, commuters, and researchers.

---

## Features

- **Route Planning**
  - **Public Transit Planner**: Find optimal routes using integrated bus and metro networks, with options to prefer metro or minimize transfers. Visualizes routes, transfer points, and traffic lights.
  - **Driving Assist**: Plan driving routes using Dijkstra, A*, and MST algorithms, considering road conditions, traffic lights, and real-time scenarios (e.g., road closures, rush hour).

- **Schedule Optimization**
  - Dynamic programming-based allocation of buses and trains to maximize network efficiency and meet demand.
  - Generates optimized schedules and visualizes resource allocation.

- **Network Analytics & Reports**
  - Interactive dashboards for infrastructure, population, connectivity, and facilities.
  - Visual and statistical reports using Plotly and Folium.

- **Network Status**
  - Real-time simulation and visualization of traffic, bus, and metro networks.
  - Color-coded maps for bus routes and metro lines with legends.

- **Data Management**
  - Explore, search, and download all core datasets (neighborhoods, roads, facilities, bus routes, metro lines, traffic lights).

---

## Tech Stack

- **Frontend/UI**: [Streamlit](https://streamlit.io/), [streamlit-folium](https://github.com/randyzwitch/streamlit-folium)
- **Data Processing**: [pandas](https://pandas.pydata.org/), [numpy](https://numpy.org/)
- **Graph Algorithms**: [networkx](https://networkx.org/)
- **Mapping & Visualization**: [folium](https://python-visualization.github.io/folium/), [plotly](https://plotly.com/python/)
- **Other**: [fontawesome-markdown](https://pypi.org/project/fontawesome-markdown/), [pathlib](https://docs.python.org/3/library/pathlib.html)

---

## Project Structure

```
Smart-City-Transportation-Optimization-System/
│
├── UI/
│   ├── app.py                # Main Streamlit app (modularized)
│   └── components/           # UI components (transit planner, reports, maps, etc.)
│
├── algorithms/               # Routing and optimization algorithms (Dijkstra, A*, MST, DP)
├── controller/               # Main controller for data, logic, and orchestration
├── utils/                    # Helper functions, data loaders, traffic light logic, visualization
├── data/                     # CSV data files (neighborhoods, roads, facilities, transit, etc.)
├── tests/                    # Unit tests for algorithms and components
├── requirements.txt          # Python dependencies
├── main.py                   # Entry point (verifies data, launches app)
└── .streamlit/               # Streamlit configuration
```

---

## Getting Started

### 1. Prerequisites

- Python 3.9 or higher
- All required data files in the `data/` directory:
  - `neighborhoods.csv`
  - `roads.csv`
  - `facilities.csv`
  - `bus_routes.csv`
  - `metro_lines.csv`
  - `demand_data.csv`

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/ramez-asaad/Smart-City-Transportation-Optimization-System.git
cd Smart-City-Transportation-Optimization-System
pip install -r requirements.txt
```

### 3. Running the App

```bash
streamlit run main.py
```

The app will open in your browser. If any required data files are missing, you’ll be prompted to add them.

---

## Usage

- **Dashboard**: View city metrics, plan routes, simulate network status, and optimize schedules.
- **Data**: Browse, search, and download all datasets.
- **Reports**: Access analytics and visual reports on infrastructure, population, and connectivity.

---

## Customization

- **Data**: Replace or update CSV files in the `data/` directory to reflect your city or scenario.
- **Algorithms**: Extend or modify algorithms in the `algorithms/` folder for custom routing or optimization logic.
- **UI**: Adjust or add UI components in `UI/components/` for new features or visualizations.

---

## Testing

Unit tests are provided for core algorithms. To run tests:

```bash
python -m unittest discover tests
```

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or improvements.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- Inspired by real-world urban mobility challenges.
- Built with open-source libraries and data science tools.

---

**CityWise** – Smart Urban Transportation for the Cities of Tomorrow.

---
