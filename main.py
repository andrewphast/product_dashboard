import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import base64
from io import BytesIO
from PIL import Image
import numpy as np
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load the CSV file into a pandas DataFrame
df = pd.read_csv(os.path.join(current_dir, "data/20250403_Log_analysis_looker.csv"))

# Ensure that the assayID column is treated as a string
df['assayID'] = df['assayID'].astype(str)

# Create a new column 'Instrument' by taking the first 4 characters of the assayID
df['Instrument'] = df['assayID'].str[:4]

# Filter out non-integer batch numbers and convert to integers
df['chipBatch'] = pd.to_numeric(df['chipBatch'], errors='coerce')
df = df.dropna(subset=['chipBatch'])
df['chipBatch'] = df['chipBatch'].astype(int)

# Load and encode the logo
def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

logo_base64 = get_base64_encoded_image(os.path.join(current_dir, "assets/phast_logo.png"))

# Create violin plot with box plot overlay for chip lots
def create_violin_plot(data, group_by, title):
    fig = px.violin(
        data,
        x=group_by,
        y="sample_loading_time",
        box=True,  # Show box plot inside violin
        points="all",  # Show all points
        title=title,
        labels={
            group_by: group_by,
            "sample_loading_time": "Sample Loading Time (seconds)"
        },
        hover_data=['assayID']  # Add assay ID to tooltip
    )
    fig.update_layout(
        title_x=0.5,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True,
        violinmode='group'
    )
    return fig

# Create box plots for other groupings
def create_boxplot(data, group_by, title):
    fig = px.box(
        data,
        x=group_by,
        y="sample_loading_time",
        points="all",
        title=title,
        labels={
            group_by: group_by,
            "sample_loading_time": "Sample Loading Time (seconds)"
        },
        hover_data=['assayID']  # Add assay ID to tooltip
    )
    fig.update_layout(
        title_x=0.5,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True
    )
    return fig

# Create radar chart for batch comparison
def create_radar_plot(data, batch1, batch2):
    # Filter data for the two batches
    filtered_data = data[data['chipBatch'].isin([batch1, batch2])]
    
    # Calculate statistics for each batch
    stats = filtered_data.groupby('chipBatch').agg({
        'sample_loading_time': ['mean', 'std', 'min', 'max', 'count']
    }).reset_index()
    
    # Create radar chart data
    categories = ['Mean Time', 'Standard Deviation', 'Min Time', 'Max Time']
    
    fig = go.Figure()
    
    for batch in [batch1, batch2]:
        batch_stats = stats[stats['chipBatch'] == batch].iloc[0]
        fig.add_trace(go.Scatterpolar(
            r=[
                batch_stats[('sample_loading_time', 'mean')],
                batch_stats[('sample_loading_time', 'std')],
                batch_stats[('sample_loading_time', 'min')],
                batch_stats[('sample_loading_time', 'max')]
            ],
            theta=categories,
            fill='toself',
            name=f'Batch {batch}',
            customdata=filtered_data[filtered_data['chipBatch'] == batch]['assayID'].values,
            hovertemplate='<b>%{theta}</b>: %{r:.2f} seconds<br>Assay ID: %{customdata}<extra></extra>'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(stats[('sample_loading_time', 'max')].max(), 
                            stats[('sample_loading_time', 'count')].max())]
            )
        ),
        title=f'Batch Comparison: {batch1} vs {batch2}',
        title_x=0.5,
        showlegend=True
    )
    
    return fig

# Create bar plot for comparison
def create_bar_plot(data, group_type, value1, value2):
    filtered_data = data[data[group_type].isin([value1, value2])]
    # Calculate mean and standard deviation for each group
    stats = filtered_data.groupby(group_type)['sample_loading_time'].agg(['mean', 'std']).reset_index()
    
    fig = px.bar(
        stats,
        x=group_type,
        y='mean',
        error_y='std',
        title=f"Comparison: {value1} vs {value2}",
        labels={
            group_type: group_type,
            'mean': 'Average Sample Loading Time (seconds)',
            'std': 'Standard Deviation'
        }
    )
    fig.update_layout(
        title_x=0.5,
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True
    )
    return fig

# Create three different views
chip_lot_fig = create_violin_plot(df, "chipLot", "Sample Loading Time Distribution by Chip Lot")
chip_batch_fig = create_boxplot(df, "chipBatch", "Sample Loading Time by Chip Batch")
instrument_fig = create_boxplot(df, "Instrument", "Sample Loading Time by Instrument")

# Get unique values for dropdowns
unique_chip_batches = sorted(df['chipBatch'].unique())
unique_instruments = sorted(df['Instrument'].unique())

# Create initial comparison plots
batch_comparison_fig = create_radar_plot(
    df,
    unique_chip_batches[0],
    unique_chip_batches[1]
)

# Create initial instrument comparison plot with box and swarm plot
def create_instrument_comparison_plot(data, instrument1, instrument2):
    filtered_data = data[data['Instrument'].isin([instrument1, instrument2])]
    
    fig = go.Figure()
    
    # Add box plots
    for i, instrument in enumerate([instrument1, instrument2]):
        instrument_data = filtered_data[filtered_data['Instrument'] == instrument]
        fig.add_trace(go.Box(
            y=instrument_data['sample_loading_time'],
            name=f'Instrument {instrument}',
            boxpoints=False,
            marker_color='rgba(31, 119, 180, 0.5)' if i == 0 else 'rgba(255, 127, 14, 0.5)',
            line_color='rgb(31, 119, 180)' if i == 0 else 'rgb(255, 127, 14)'
        ))
        
        # Add swarm plot points
        fig.add_trace(go.Scatter(
            y=instrument_data['sample_loading_time'],
            x=[i] * len(instrument_data),
            mode='markers',
            name=f'Instrument {instrument} Points',
            marker=dict(
                color='rgba(31, 119, 180, 0.7)' if i == 0 else 'rgba(255, 127, 14, 0.7)',
                size=8
            ),
            showlegend=False,
            customdata=instrument_data['assayID'].values,
            hovertemplate='<b>Loading Time</b>: %{y:.2f} seconds<br>Assay ID: %{customdata}<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Instrument Comparison: {instrument1} vs {instrument2}',
        title_x=0.5,
        xaxis=dict(
            title='Instrument',
            ticktext=[instrument1, instrument2],
            tickvals=[0, 1],
            range=[-0.5, 1.5]
        ),
        yaxis=dict(
            title='Sample Loading Time (seconds)'
        ),
        showlegend=True,
        boxmode='group',
        boxgap=0.3,
        boxgroupgap=0.3
    )
    
    return fig

instrument_comparison_fig = create_instrument_comparison_plot(
    df,
    unique_instruments[0],
    unique_instruments[1]
)

# Create HTML with all plots and dropdowns
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PhAST Instrument Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            position: relative;
        }}
        .logo {{
            height: 50px;
            position: absolute;
            left: 0;
        }}
        h1 {{
            color: #2c3e50;
            margin: 0;
            text-align: center;
        }}
        .plot-container {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .comparison-controls {{
            display: flex;
            gap: 20px;
            margin-bottom: 10px;
            justify-content: center;
        }}
        select {{
            padding: 5px;
            border-radius: 4px;
            border: 1px solid #ccc;
            min-width: 150px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <img src="data:image/png;base64,{logo_base64}" class="logo" alt="PhAST Logo">
        <h1>PhAST Instrument Dashboard</h1>
    </div>

    <div class="plot-container">
        {chip_lot_fig.to_html(full_html=False)}
    </div>
    <div class="plot-container">
        {chip_batch_fig.to_html(full_html=False)}
    </div>
    <div class="plot-container">
        {instrument_fig.to_html(full_html=False)}
    </div>

    <div class="plot-container">
        <h2>Batch Comparison</h2>
        <div class="comparison-controls">
            <select id="batch1">
                {''.join(f'<option value="{batch}">{batch}</option>' for batch in unique_chip_batches)}
            </select>
            <select id="batch2">
                {''.join(f'<option value="{batch}">{batch}</option>' for batch in unique_chip_batches)}
            </select>
        </div>
        <div id="batch-comparison">
            {batch_comparison_fig.to_html(full_html=False)}
        </div>
    </div>

    <div class="plot-container">
        <h2>Instrument Comparison</h2>
        <div class="comparison-controls">
            <select id="instrument1">
                {''.join(f'<option value="{inst}">{inst}</option>' for inst in unique_instruments)}
            </select>
            <select id="instrument2">
                {''.join(f'<option value="{inst}">{inst}</option>' for inst in unique_instruments)}
            </select>
        </div>
        <div id="instrument-comparison">
            {instrument_comparison_fig.to_html(full_html=False)}
        </div>
    </div>

    <script>
        // Function to update comparison plot
        function updateComparisonPlot(plotId, groupType, select1, select2) {{
            const value1 = document.getElementById(select1).value;
            const value2 = document.getElementById(select2).value;
            
            // Filter data for the selected values
            const data = {df.to_json(orient='records')};
            const filteredData = data.filter(d => d[groupType] === value1 || d[groupType] === value2);
            
            if (groupType === 'chipBatch') {{
                // Calculate statistics for radar chart
                const stats = filteredData.reduce((acc, d) => {{
                    const batchVal = parseInt(d[groupType]);
                    if (!acc[batchVal]) {{
                        acc[batchVal] = {{ 
                            sum: 0, 
                            count: 0, 
                            values: [],
                            min: Infinity,
                            max: -Infinity
                        }};
                    }}
                    acc[batchVal].sum += d.sample_loading_time;
                    acc[batchVal].count += 1;
                    acc[batchVal].values.push(d.sample_loading_time);
                    acc[batchVal].min = Math.min(acc[batchVal].min, d.sample_loading_time);
                    acc[batchVal].max = Math.max(acc[batchVal].max, d.sample_loading_time);
                    return acc;
                }}, {{}});
                
                // Calculate standard deviation
                Object.keys(stats).forEach(key => {{
                    const mean = stats[key].sum / stats[key].count;
                    const variance = stats[key].values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / stats[key].count;
                    stats[key].std = Math.sqrt(variance);
                    stats[key].mean = mean;
                }});
                
                // Create radar chart
                const categories = ['Mean Time', 'Standard Deviation', 'Min Time', 'Max Time'];
                const traces = [];
                
                // Add trace for first batch
                traces.push({{
                    type: 'scatterpolar',
                    r: [
                        stats[value1].mean,
                        stats[value1].std,
                        stats[value1].min,
                        stats[value1].max
                    ],
                    theta: categories,
                    fill: 'toself',
                    name: `Batch ${{value1}}`
                }});
                
                // Add trace for second batch
                traces.push({{
                    type: 'scatterpolar',
                    r: [
                        stats[value2].mean,
                        stats[value2].std,
                        stats[value2].min,
                        stats[value2].max
                    ],
                    theta: categories,
                    fill: 'toself',
                    name: `Batch ${{value2}}`
                }});
                
                // Find the maximum value for scaling (excluding count)
                const maxValue = Math.max(
                    stats[value1].max,
                    stats[value2].max
                );
                
                // Update the plot
                Plotly.newPlot(plotId, traces, {{
                    polar: {{
                        radialaxis: {{
                            visible: true,
                            range: [0, maxValue * 1.1]  // Add 10% padding
                        }}
                    }},
                    title: `Batch Comparison: ${{value1}} vs ${{value2}}`,
                    title_x: 0.5,
                    showlegend: true
                }});
            }} else {{
                // Filter data for the selected instruments
                const instrument1Data = filteredData.filter(d => d[groupType] === value1).map(d => d.sample_loading_time);
                const instrument2Data = filteredData.filter(d => d[groupType] === value2).map(d => d.sample_loading_time);
                
                // Create box plot with swarm plot overlay
                const traces = [];
                
                // Add box plot trace for first instrument
                traces.push({{
                    type: 'box',
                    y: instrument1Data,
                    name: `Instrument ${{value1}}`,
                    boxpoints: false,
                    marker: {{ color: 'rgba(31, 119, 180, 0.5)' }},
                    line: {{ color: 'rgb(31, 119, 180)' }}
                }});
                
                // Add box plot trace for second instrument
                traces.push({{
                    type: 'box',
                    y: instrument2Data,
                    name: `Instrument ${{value2}}`,
                    boxpoints: false,
                    marker: {{ color: 'rgba(255, 127, 14, 0.5)' }},
                    line: {{ color: 'rgb(255, 127, 14)' }}
                }});
                
                // Add swarm plot traces
                traces.push({{
                    type: 'scatter',
                    y: instrument1Data,
                    x: Array(instrument1Data.length).fill(0),
                    mode: 'markers',
                    name: `Instrument ${{value1}} Points`,
                    marker: {{ 
                        color: 'rgba(31, 119, 180, 0.7)',
                        size: 8
                    }},
                    showlegend: false
                }});
                
                traces.push({{
                    type: 'scatter',
                    y: instrument2Data,
                    x: Array(instrument2Data.length).fill(1),
                    mode: 'markers',
                    name: `Instrument ${{value2}} Points`,
                    marker: {{ 
                        color: 'rgba(255, 127, 14, 0.7)',
                        size: 8
                    }},
                    showlegend: false
                }});
                
                // Update the plot
                Plotly.newPlot(plotId, traces, {{
                    title: `Instrument Comparison: ${{value1}} vs ${{value2}}`,
                    title_x: 0.5,
                    xaxis: {{
                        title: 'Instrument',
                        ticktext: [`${{value1}}`, `${{value2}}`],
                        tickvals: [0, 1],
                        range: [-0.5, 1.5]  // Add some padding to the x-axis
                    }},
                    yaxis: {{
                        title: 'Sample Loading Time (seconds)'
                    }},
                    showlegend: true,
                    boxmode: 'group'
                }});
            }}
        }}

        // Add event listeners for dropdowns
        document.getElementById('batch1').addEventListener('change', () => updateComparisonPlot('batch-comparison', 'chipBatch', 'batch1', 'batch2'));
        document.getElementById('batch2').addEventListener('change', () => updateComparisonPlot('batch-comparison', 'chipBatch', 'batch1', 'batch2'));
        document.getElementById('instrument1').addEventListener('change', () => updateComparisonPlot('instrument-comparison', 'Instrument', 'instrument1', 'instrument2'));
        document.getElementById('instrument2').addEventListener('change', () => updateComparisonPlot('instrument-comparison', 'Instrument', 'instrument1', 'instrument2'));
    </script>
</body>
</html>
"""

# Save the HTML file
with open(os.path.join(current_dir, "index.html"), "w") as f:
    f.write(html_content)

print("Dashboard has been generated as 'index.html'. You can open it in your web browser.")
