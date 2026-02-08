"""
Trade Analysis Visualization: Distribution of P&L, win/loss by ticker, exit reasons.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

def create_trade_analysis(trades_file, output_file):
    """Create comprehensive trade analysis charts."""
    # Load data
    trades_df = pd.read_csv(trades_file)
    
    if len(trades_df) == 0:
        print("⚠ No trades to visualize")
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'P&L Distribution (Individual Trades)',
            'Win/Loss Count by Ticker',
            'Days Held Distribution',
            'Exit Reason Breakdown'
        ),
        specs=[
            [{'type': 'histogram'}, {'type': 'bar'}],
            [{'type': 'histogram'}, {'type': 'pie'}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.12
    )
    
    # 1. P&L Distribution
    fig.add_trace(
        go.Histogram(
            x=trades_df['pnl_pct'],
            nbinsx=15,
            marker=dict(
                color=trades_df['pnl_pct'],
                colorscale=[[0, '#D62828'], [0.5, '#FFBA08'], [1, '#06A77D']],
                line=dict(width=1, color='white')
            ),
            name='P&L Distribution',
            hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 2. Win/Loss by Ticker
    win_loss_by_ticker = trades_df.groupby('ticker').apply(
        lambda x: pd.Series({
            'wins': (x['pnl'] > 0).sum(),
            'losses': (x['pnl'] <= 0).sum()
        })
    ).reset_index()
    
    fig.add_trace(
        go.Bar(
            x=win_loss_by_ticker['ticker'],
            y=win_loss_by_ticker['wins'],
            name='Wins',
            marker_color='#06A77D',
            hovertemplate='<b>%{x}</b><br>Wins: %{y}<extra></extra>'
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(
            x=win_loss_by_ticker['ticker'],
            y=win_loss_by_ticker['losses'],
            name='Losses',
            marker_color='#D62828',
            hovertemplate='<b>%{x}</b><br>Losses: %{y}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 3. Days Held Distribution
    fig.add_trace(
        go.Histogram(
            x=trades_df['days_held'],
            nbinsx=10,
            marker=dict(color='#2E86AB', line=dict(width=1, color='white')),
            name='Days Held',
            hovertemplate='Days: %{x}<br>Count: %{y}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 4. Exit Reason Pie Chart
    exit_reasons = trades_df['exit_reason'].value_counts()
    colors = {'stop_loss': '#D62828', 'take_profit': '#06A77D', 
              'hold_period': '#FFBA08', 'end_of_backtest': '#A6A6A6'}
    
    fig.add_trace(
        go.Pie(
            labels=exit_reasons.index,
            values=exit_reasons.values,
            marker=dict(colors=[colors.get(r, '#2E86AB') for r in exit_reasons.index]),
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'Trade Analysis: {len(trades_df)} Trades<br>' +
                 f'<sub>Win Rate: {(trades_df["pnl"] > 0).sum() / len(trades_df) * 100:.1f}% | ' +
                 f'Avg P&L: ${trades_df["pnl"].mean():,.2f} ({trades_df["pnl_pct"].mean():+.2f}%)</sub>',
            x=0.5,
            xanchor='center'
        ),
        height=800,
        showlegend=True,
        template='plotly_white'
    )
    
    # Update axes
    fig.update_xaxes(title_text="Return (%)", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    
    fig.update_xaxes(title_text="Ticker", row=1, col=2)
    fig.update_yaxes(title_text="Number of Trades", row=1, col=2)
    
    fig.update_xaxes(title_text="Days Held", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    
    # Save
    output_path = Path(output_file)
    fig.write_html(str(output_path))
    
    try:
        png_path = output_path.with_suffix('.png')
        fig.write_image(str(png_path), width=1400, height=800)
        print(f"✓ Saved PNG: {png_path}")
    except:
        print(f"  (PNG export skipped: pip install kaleido)")
    
    print(f"✓ Saved HTML: {output_path}")
    
    return fig

if __name__ == '__main__':
    trades_dir = Path(__file__).parent.parent / 'trades'
    trade_files = sorted(trades_dir.glob('trade_log_*.csv'))
    
    if not trade_files:
        print("❌ No trade data found. Run scripts/07_backtest.py first.")
        sys.exit(1)
    
    latest_trades = trade_files[-1]
    timestamp = latest_trades.stem.split('_')[-1]
    output_file = trades_dir / f'trade_analysis_{timestamp}.html'
    
    print("Creating trade analysis charts...")
    fig = create_trade_analysis(latest_trades, output_file)
    print("✓ Done!")
