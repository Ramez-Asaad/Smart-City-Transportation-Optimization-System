import streamlit as st
import pandas as pd
import folium
import networkx as nx
from streamlit_folium import st_folium

# ------------------------
# 1. Load and clean data
# ------------------------
@st.cache_data
def load_data():
    neighborhoods = pd.read_csv("neighborhoods.csv")
    roads = pd.read_csv("roads.csv")
    facilities = pd.read_csv("facilities.csv")
    
    for df in [neighborhoods, roads, facilities]:
        df.columns = df.columns.str.strip()
    
    return neighborhoods, roads, facilities

neighborhoods, roads, facilities = load_data()

# ------------------------
# 2. Build node positions
# ------------------------
neighborhood_ids = neighborhoods["ID"].astype(str).tolist()

node_positions = {
    str(row["ID"]): (row["Y-coordinate"], row["X-coordinate"])
    for _, row in neighborhoods.iterrows()
}
facility_positions = {
    str(row["ID"]): (row["Y-coordinate"], row["X-coordinate"])
    for _, row in facilities.iterrows()
}

# ------------------------
# 3. Sidebar UI
# ------------------------
st.sidebar.title("Choose Algorithm")
algorithm = st.sidebar.radio("Feature Group", [
    "Minimum Spanning Tree Algorithm",
    "Shortest Path Algorithms",
    "Dynamic Programming Solutions",
    "Greedy Algorithm Application",
    "None"
])

show_facilities = st.sidebar.checkbox("Show Facilities", value=True)

# ------------------------
# 4. Create base map
# ------------------------
m = folium.Map(location=[
    neighborhoods["Y-coordinate"].mean(),
    neighborhoods["X-coordinate"].mean()
], zoom_start=12)

# --- Neighborhoods (blue) ---
for _, row in neighborhoods.iterrows():
    folium.CircleMarker(
        location=[row["Y-coordinate"], row["X-coordinate"]],
        radius=6,
        color="blue",
        fill=True,
        fill_opacity=0.8,
        popup=f"{row['Name']}<br>Population: {row['Population']}"
    ).add_to(m)

# --- Facilities (red, optional) ---
if show_facilities:
    for _, row in facilities.iterrows():
        folium.Marker(
            location=[row["Y-coordinate"], row["X-coordinate"]],
            icon=folium.Icon(color="red", icon="info-sign"),
            popup=f"{row['Name']} ({row['Type']})"
        ).add_to(m)

# --- Roads (gray) ---
roads["FromID"] = roads["FromID"].astype(str).str.strip()
roads["ToID"] = roads["ToID"].astype(str).str.strip()
neighborhood_ids_str = neighborhoods["ID"].astype(str).str.strip().tolist()

for _, row in roads.iterrows():
    from_id, to_id = row["FromID"], row["ToID"]
    if from_id in node_positions and to_id in node_positions:
        folium.PolyLine(
            [node_positions[from_id], node_positions[to_id]],
            color="gray", weight=1, opacity=0.4
        ).add_to(m)

# ------------------------
# 5. MST Algorithm
# ------------------------
if algorithm == "Minimum Spanning Tree Algorithm":
    mst_graph = nx.Graph()

    for _, row in roads.iterrows():
        from_id, to_id = row["FromID"], row["ToID"]
        if from_id in neighborhood_ids_str and to_id in neighborhood_ids_str:
            mst_graph.add_edge(from_id, to_id, weight=row["Distance(km)"])

    # Stats: nodes/edges before MST
    st.sidebar.markdown("### 🧠 Graph Summary")
    st.sidebar.info(f"🏙️ **Connected Neighborhoods:** {len(mst_graph.nodes())}")
    st.sidebar.info(f"🛣️ **Available Road Connections:** {len(mst_graph.edges())}")

    if len(mst_graph.edges()) > 0:
        # Build MST
        prim_mst = nx.minimum_spanning_tree(mst_graph, algorithm="prim")

        for u, v in prim_mst.edges():
            folium.PolyLine(
                [node_positions[u], node_positions[v]],
                color="green", weight=3,
                tooltip=f"Prim MST: {u} — {v}"
            ).add_to(m)

        total_dist = sum(mst_graph[u][v]['weight'] for u, v in prim_mst.edges())

        st.sidebar.markdown("### 🌿 MST Result (Prim’s Algorithm)")
        st.sidebar.success(f"🌿 **Roads in MST:** {len(prim_mst.edges())}")
        st.sidebar.info(f"📏 **Total MST Distance:** {total_dist:.2f} km")
    else:
        st.sidebar.warning("⚠️ No valid roads between neighborhoods!")

# ------------------------
# 6. Display map
# ------------------------
st.title("Cairo Smart Transportation Network")
st.markdown("**Blue** = Neighborhoods, **Gray** = All Roads, **Green** = MST<br>**Red** = Facilities (optional)", unsafe_allow_html=True)
st_folium(m, width=800, height=600)
