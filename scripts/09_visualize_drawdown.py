"""
Drawdown Chart Visualization: Show underwater equity and recovery periods.
"""

import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys

def create_drawdown_chart(equity_file, output_file):
    """Create interactive drawdown chart."""
    # Load data
    equity_df = pd.read_csv(equity_file)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    
    # Calculate drawdown
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] / equity_df['peak']) - 1
    equity_df['drawdown_pct'] = equity_df['drawdown'] * 100
    
    # Find max drawdown
    max_dd_idx = equity_df['drawdown'].idxmin()
    max_dd_value = equity_df.loc[max_dd_idx, 'drawdown_pct']
    max_dd_date = equity_df.loc[max_dd_idx, 'date']
    
    # Create figure
    fig = go.Figure()
    
    # Drawdown area
    fig.add_trace(
        go.Scatter(
            x=equity_df['date'],
            y=equity_df['drawdown_pct'],
            mode='lines',
            name='Drawdown',
            line=dict(color='#D62828', width=0),
            fill='tozeroy',
            fillcolor='rgba(214, 40, 40, 0.3)',
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Drawdown: %{y:.2f}%<extra></extra>'
        )
    )
    
    # Add max drawdown annotation
    fig.add_annotation(
        x=max_dd_date,
        y=max_dd_value,
        text=f'Max DD: {max_dd_value:.2f}%',
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor='#D62828',
        ax=50,
        ay=-50,
        bgcolor='white',
        bordercolor='#D62828',
        borderwidth=2
    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'Portfolio Drawdown Analysis<br>' +
                 f'<sub>Maximum Drawdown: {max_dd_value:.2f}% on {max_dd_date.strftime("%Y-%m-%d")}</sub>',
            x=0.5,
            xanchor='center'
        ),
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        height=500,
        showlegend=False,
        hovermode='x',
        template='plotly_white'
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    
    # Save
    output_path = Path(output_file)
    fig.write_html(str(output_path))
    
    try:
        png_path = output_path.with_suffix('.png')
        fig.write_image(str(png_path), width=1200, height=500)
        print(f"✓ Saved PNG: {png_path}")
    except:
        print(f"  (PNG export skipped: pip install kaleido)")
    
    print(f"✓ Saved HTML: {output_path}")
    
    return fig

if __name__ == '__main__':
    trades_dir = Path(__file__).parent.parent / 'trades'
    equity_files = sorted(trades_dir.glob('daily_equity_*.csv'))
    
    if not equity_files:
        print("❌ No equity data found. Run scripts/07_backtest.py first.")
        sys.exit(1)
    
    latest_equity = equity_files[-1]
    timestamp = latest_equity.stem.split('_')[-1]
    output_file = trades_dir / f'drawdown_chart_{timestamp}.html'
    
    print("Creating drawdown chart...")
    fig = create_drawdown_chart(latest_equity, output_file)
    print("✓ Done!")
