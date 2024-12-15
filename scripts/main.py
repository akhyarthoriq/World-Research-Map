import geopandas as gpd
import pandas as pd
import folium
from branca.colormap import linear

# Load high-resolution world shapefile
# Replace 'path_to_shapefile' with the actual path to your downloaded shapefile
shapefile_path = '../data/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp'
world = gpd.read_file(shapefile_path)

# Reading Scimago data
scimagojr_path = '../data/scimagojr country rank 1996-2023.xlsx'
scimagojr_df = pd.read_excel(scimagojr_path, sheet_name='Sheet1')

# Columns to rank
ranking_columns = ['H index', 'Documents', 'Citations per document']

# Create ranks for each specified column
for col in ranking_columns:
    # Calculate the total valid entries (non-NaN) for the column
    total_rank = scimagojr_df[col].count()
    
    # Rank the column and format as 'rank/total'
    rank_col_name = f'Rank ({col})'
    scimagojr_df[rank_col_name] = scimagojr_df[col].rank(ascending=False, method='min')\
        .apply(lambda x: f"{int(x)}/{total_rank}")  # Format rank with total

# Load the researcher density data
researcher_density_path = '../data/researchers-in-rd-per-million-people.csv'
researcher_density = pd.read_csv(researcher_density_path)

# Latest data update
latest_year = researcher_density.groupby('Code')['Year'].max().reset_index()
latest_year.head()

research_density_newest = pd.merge(
    latest_year,
    researcher_density,
    on=['Code', 'Year'],
    how='left'
)

# Merge GeoDataFrame with Pandas DataFrame on the ISO country codes
merged = world.merge(research_density_newest, left_on='ADM0_A3', right_on='Code', how='left')
merged = merged.merge(scimagojr_df, left_on='Entity', right_on='Country', how='left')

# Convert the 'Year' column to string type
merged['Year'] = merged['Year'].fillna(0).astype(int).astype(str)

# Extract relevant column and drop NaN
research_density_values = merged['Researchers in R&D (per million people)'].dropna()

# Normalize the researcher density values for the colormap
min_density = merged['Researchers in R&D (per million people)'].min()
max_density = merged['Researchers in R&D (per million people)'].max()
colormap = linear.YlGnBu_05.to_step(n=6, data=research_density_values, method="quantiles", round_method="int").scale(min_density, max_density)
colormap.caption = 'Researchers in R&D (per million people)'

# Create a Folium map with a restricted maximum zoom-out
m = folium.Map(
    location=[20, 0],  # Center of the map
    zoom_start=2,      # Initial zoom level
    min_zoom=2,        # Minimum zoom level
    tiles='CartoDB Positron',
    max_bounds=True,    # Restrict panning to map bounds
    control_scale=True,  # Add scale control for better visualization
)

# Add a Choropleth layer to the map
folium.GeoJson(
    merged.to_json(),  # Convert GeoDataFrame to GeoJSON
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties']['Researchers in R&D (per million people)'])
        if feature['properties']['Researchers in R&D (per million people)'] is not None else '///',
        'color': 'black',
        'weight': 0.8,
        'fillOpacity': 0.8,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['ADMIN', 'Year', 'Researchers in R&D (per million people)', 'Rank (Documents)', 'Rank (Citations per document)', 'Rank (H index)'],  # 'ADMIN' holds the country name
        aliases=['Country', 'Latest Update', 'Researchers per Million', 'Document Rank (1996-2023)', 'Citations per Document Rank (1996-2023)', 'H Index Rank (1996-2023)'],
        localize=True
    )
).add_to(m)

# Add the colormap to the map
colormap.add_to(m)

# Save and display the map
m.save('../result/high_resolution_research_density_map.html')

# Export the GeoDataFrame to a GeoJSON file
output_geojson_path = "../result/research_density_map.geojson"
merged.to_file(output_geojson_path, driver="GeoJSON")
