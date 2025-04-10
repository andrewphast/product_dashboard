import pandas as pd
import plotly.express as px
import plotly.io as pio
import base64
from io import BytesIO
from PIL import Image
import numpy as np

# Load the CSV file into a pandas DataFrame
df = pd.read_csv("data/20250403_Log_analysis_looker.csv")

# Ensure that the assayID column is treated as a string
df['assayID'] = df['assayID'].astype(str)

# Create a new column 'Instrument' by taking the first 4 characters of the assayID
df['Instrument'] = df['assayID'].str[:4]

# Filter out non-integer batch numbers
df['chipBatch'] = pd.to_numeric(df['chipBatch'], errors='coerce')
df = df.dropna(subset=['chipBatch'])
df['chipBatch'] = df['chipBatch'].astype(int)

# Load and encode the logo
def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

logo_base64 = get_base64_encoded_image("assets/phast_logo.png")

# Create box plots for different groupings
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
        }
    )
    fig.update_layout(
        title_x=0.5,
        margin=dict(l=40, r=40, t=60, b=40),
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
chip_lot_fig = create_boxplot(df, "chipLot", "Sample Loading Time by Chip Lot")
chip_batch_fig = create_boxplot(df, "chipBatch", "Sample Loading Time by Chip Batch")
instrument_fig = create_boxplot(df, "Instrument", "Sample Loading Time by Instrument")

# Get unique values for dropdowns
unique_chip_batches = sorted(df['chipBatch'].unique())
unique_instruments = sorted(df['Instrument'].unique())

# Create initial comparison plots
batch_comparison_fig = create_bar_plot(
    df,
    "chipBatch",
    unique_chip_batches[0],
    unique_chip_batches[1]
)

instrument_comparison_fig = create_bar_plot(
    df,
    "Instrument",
    unique_instruments[0],
    unique_instruments[1]
)

# Create HTML with all plots and dropdowns
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PhAST Product Dashboard</title>
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
        <h1>PhAST Product Dashboard</h1>
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
            
            // Calculate mean and standard deviation for each group
            const stats = filteredData.reduce((acc, d) => {{
                if (!acc[d[groupType]]) {{
                    acc[d[groupType]] = {{ sum: 0, count: 0, values: [] }};
                }}
                acc[d[groupType]].sum += d.sample_loading_time;
                acc[d[groupType]].count += 1;
                acc[d[groupType]].values.push(d.sample_loading_time);
                return acc;
            }}, {{}});
            
            // Calculate standard deviation
            Object.keys(stats).forEach(key => {{
                const mean = stats[key].sum / stats[key].count;
                const variance = stats[key].values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / stats[key].count;
                stats[key].std = Math.sqrt(variance);
                stats[key].mean = mean;
            }});
            
            // Create bar plot
            const trace = {{
                type: 'bar',
                x: [value1, value2],
                y: [stats[value1].mean, stats[value2].mean],
                error_y: {{
                    type: 'data',
                    array: [stats[value1].std, stats[value2].std],
                    visible: true
                }},
                name: 'Average Sample Loading Time'
            }};
            
            // Update the plot
            Plotly.newPlot(plotId, [trace], {{
                title: `Comparison: ${{value1}} vs ${{value2}}`,
                xaxis: {{title: groupType}},
                yaxis: {{title: 'Average Sample Loading Time (seconds)'}},
                title_x: 0.5,
                margin: {{l: 40, r: 40, t: 60, b: 40}},
                showlegend: true
            }});
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
with open("dashboard.html", "w") as f:
    f.write(html_content)

print("Dashboard has been generated as 'dashboard.html'. You can open it in your web browser.")
