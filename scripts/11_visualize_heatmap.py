"""
Monthly Returns Heatmap: Calendar visualization of monthly performance.
"""

import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys
import numpy as np

def create_monthly_heatmap(equity_file, output_file):
    """Create monthly returns heatmap."""
    # Load data
    equity_df = pd.read_csv(equity_file)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    equity_df = equity_df.set_index('date')
    
    # Calculate daily returns
    equity_df['daily_return'] = equity_df['equity'].pct_change()
    
    # Resample to monthly
    monthly_returns = equity_df['daily_return'].resample('M').apply(
        lambda x: (1 + x).prod() - 1
    ) * 100  # Convert to percentage
    
    # Create pivot table (Year x Month)
    monthly_returns_df = pd.DataFrame({
        'year': monthly_returns.index.year,
        'month': monthly_returns.index.month,
        'return': monthly_returns.values
    })
    
    pivot = monthly_returns_df.pivot(index='year', columns='month', values='return')
    
    # Month names
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[month_names[i-1] for i in pivot.columns],
        y=pivot.index,
        colorscale=[
            [0, '#D62828'],      # Red for losses
            [0.5, '#FFFFFF'],    # White for neutral
            [1, '#06A77D']       # Green for gains
        ],
        zmid=0,
        text=np.round(pivot.values, 2),
        texttemplate='%{text:.2f}%',
        textfont={"size": 12},
        colorbar=dict(title='Return (%)'),
        hovertemplate='<b>%{y} %{x}</b><br>Return: %{z:.2f}%<extra></extra>'
    ))
    
    # Calculate annual returns
    annual_returns = monthly_returns_df.groupby('year')['return'].sum()
    
    # Add annotations for best/worst months
    if len(pivot.values.flatten()) > 0:
        best_month_val = np.nanmax(pivot.values)
        worst_month_val = np.nanmin(pivot.values)
        
        best_idx = np.where(pivot.values == best_month_val)
        worst_idx = np.where(pivot.values == worst_month_val)
        
        if len(best_idx[0]) > 0:
            best_year = pivot.index[best_idx[0][0]]
            best_month = month_names[pivot.columns[best_idx[1][0]] - 1]
        
        if len(worst_idx[0]) > 0:
            worst_year = pivot.index[worst_idx[0][0]]
            worst_month = month_names[pivot.columns[worst_idx[1][0]] - 1]
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'Monthly Returns Heatmap<br>' +
                 f'<sub>Best Month: {best_month} {best_year} ({best_month_val:.2f}%) | ' +
                 f'Worst Month: {worst_month} {worst_year} ({worst_month_val:.2f}%)</sub>',
            x=0.5,
            xanchor='center'
        ),
        xaxis_title='Month',
        yaxis_title='Year',
        height=400,
        template='plotly_white'
    )
    
    # Save
    output_path = Path(output_file)
    fig.write_html(str(output_path))
    
    try:
        png_path = output_path.with_suffix('.png')
        fig.write_image(str(png_path), width=1200, height=400)
        print(f"✓ Saved PNG: {png_path}")
    except:
        print(f"  (PNG export skipped: pip install kaleido)")
    
    print(f"✓ Saved HTML: {output_path}")
    
    # Print annual summary
    print("\nAnnual Returns:")
    for year, ret in annual_returns.items():
        print(f"  {year}: {ret:+.2f}%")
    
    return fig

if __name__ == '__main__':
    trades_dir = Path(__file__).parent.parent / 'trades'
    equity_files = sorted(trades_dir.glob('daily_equity_*.csv'))
    
    if not equity_files:
        print("❌ No equity data found. Run scripts/07_backtest.py first.")
        sys.exit(1)
    
    latest_equity = equity_files[-1]
    timestamp = latest_equity.stem.split('_')[-1]
    output_file = trades_dir / f'monthly_heatmap_{timestamp}.html'
    
    print("Creating monthly returns heatmap...")
    fig = create_monthly_heatmap(latest_equity, output_file)
    print("✓ Done!")
