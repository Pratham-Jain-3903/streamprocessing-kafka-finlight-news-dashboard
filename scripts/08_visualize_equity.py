"""
Equity Curve Visualization: Interactive Plotly chart showing portfolio performance.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

def create_equity_curve(equity_file, trades_file, output_file):
    """Create interactive equity curve visualization."""
    # Load data
    equity_df = pd.read_csv(equity_file)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    
    trades_df = pd.read_csv(trades_file)
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
    trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
    
    # Load price data for TSLA and GOOGL (the stocks that generated BUY signals)
    prices_dir = Path(__file__).parent.parent / 'data' / 'prices'
    initial_capital = equity_df['equity'].iloc[0]
    start_date = equity_df['date'].iloc[0]
    
    # Function to calculate buy-and-hold equity
    def calculate_buy_hold(ticker, initial_capital, start_date, equity_dates):
        price_file = prices_dir / f'{ticker}_ohlcv.parquet'
        if not price_file.exists():
            return None
        
        prices = pd.read_parquet(price_file)
        prices.index = pd.to_datetime(prices.index)
        if prices.index.tz is not None:
            prices.index = prices.index.tz_localize(None)
        
        # Get starting price
        if start_date not in prices.index:
            # Find nearest date
            start_date_tz = start_date.tz_localize(None) if start_date.tz else start_date
            valid_dates = prices.index[prices.index >= start_date_tz]
            if len(valid_dates) == 0:
                return None
            start_date = valid_dates[0]
        
        start_price = prices.loc[start_date, 'Close']
        shares = initial_capital / start_price
        
        # Calculate equity for each date
        equity_values = []
        for date in equity_dates:
            date_tz = date.tz_localize(None) if date.tz else date
            if date_tz in prices.index:
                current_price = prices.loc[date_tz, 'Close']
                equity = shares * current_price
                equity_values.append(equity)
            else:
                # Use last known price
                valid_prices = prices[prices.index <= date_tz]
                if len(valid_prices) > 0:
                    current_price = valid_prices.iloc[-1]['Close']
                    equity = shares * current_price
                    equity_values.append(equity)
                else:
                    equity_values.append(initial_capital)
        
        return equity_values
    
    # Calculate buy-and-hold for TSLA and GOOGL
    tsla_equity = calculate_buy_hold('TSLA', initial_capital, start_date, equity_df['date'])
    googl_equity = calculate_buy_hold('GOOGL', initial_capital, start_date, equity_df['date'])
    
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=('Portfolio Equity', 'Number of Open Positions'),
        vertical_spacing=0.1
    )
    
    # Main equity curve
    fig.add_trace(
        go.Scatter(
            x=equity_df['date'],
            y=equity_df['equity'],
            mode='lines',
            name='Strategy',
            line=dict(color='#2E86AB', width=3),
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Equity: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Add TSLA buy-and-hold
    if tsla_equity:
        fig.add_trace(
            go.Scatter(
                x=equity_df['date'],
                y=tsla_equity,
                mode='lines',
                name='TSLA Buy & Hold',
                line=dict(color='#E63946', width=2, dash='dash'),
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>TSLA: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Add GOOGL buy-and-hold
    if googl_equity:
        fig.add_trace(
            go.Scatter(
                x=equity_df['date'],
                y=googl_equity,
                mode='lines',
                name='GOOGL Buy & Hold',
                line=dict(color='#06A77D', width=2, dash='dash'),
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>GOOGL: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Initial capital line
    initial_capital = equity_df['equity'].iloc[0]
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text="Initial Capital",
        annotation_position="right",
        row=1, col=1
    )
    
    # Add trade entry markers
    entry_markers = trades_df.merge(
        equity_df[['date', 'equity']], 
        left_on='entry_date', 
        right_on='date',
        how='left'
    )
    
    fig.add_trace(
        go.Scatter(
            x=entry_markers['entry_date'],
            y=entry_markers['equity'],
            mode='markers',
            name='Trade Entry',
            marker=dict(
                symbol='triangle-up',
                size=10,
                color='green',
                line=dict(width=1, color='darkgreen')
            ),
            hovertemplate='<b>BUY %{customdata[0]}</b><br>' +
                         'Date: %{x|%Y-%m-%d}<br>' +
                         'Entry Price: $%{customdata[1]:.2f}<br>' +
                         'Sentiment: %{customdata[2]:.3f}<extra></extra>',
            customdata=entry_markers[['ticker', 'entry_price', 'sentiment']].values
        ),
        row=1, col=1
    )
    
    # Number of positions
    fig.add_trace(
        go.Scatter(
            x=equity_df['date'],
            y=equity_df['num_positions'],
            mode='lines',
            name='Open Positions',
            line=dict(color='#A23B72', width=2),
            fill='tozeroy',
            fillcolor='rgba(162, 59, 114, 0.2)',
            hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Positions: %{y}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Update layout
    final_equity = equity_df['equity'].iloc[-1]
    total_return_pct = (final_equity / initial_capital - 1) * 100
    
    # Calculate buy-and-hold returns
    tsla_return = ((tsla_equity[-1] / initial_capital - 1) * 100) if tsla_equity else 0
    googl_return = ((googl_equity[-1] / initial_capital - 1) * 100) if googl_equity else 0
    
    fig.update_layout(
        title=dict(
            text=f'Sentiment Trading Strategy vs Buy & Hold<br>' +
                 f'<sub>Strategy: {total_return_pct:+.2f}% | TSLA B&H: {tsla_return:+.2f}% | GOOGL B&H: {googl_return:+.2f}% | '
                 f'Trades: {len(trades_df)} | Win Rate: {(trades_df["pnl"] > 0).sum() / len(trades_df) * 100:.1f}%</sub>',
            x=0.5,
            xanchor='center'
        ),
        height=700,
        showlegend=True,
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Update axes
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Positions", row=2, col=1)
    
    # Save
    output_path = Path(output_file)
    fig.write_html(str(output_path))
    
    # Also save as PNG if kaleido is available
    try:
        png_path = output_path.with_suffix('.png')
        fig.write_image(str(png_path), width=1200, height=700)
        print(f"✓ Saved PNG: {png_path}")
    except Exception as e:
        print(f"  (PNG export skipped: pip install kaleido)")
    
    print(f"✓ Saved HTML: {output_path}")
    
    return fig

if __name__ == '__main__':
    # Find latest backtest files
    trades_dir = Path(__file__).parent.parent / 'trades'
    
    equity_files = sorted(trades_dir.glob('daily_equity_*.csv'))
    trade_files = sorted(trades_dir.glob('trade_log_*.csv'))
    
    if not equity_files or not trade_files:
        print("❌ No backtest results found. Run scripts/07_backtest.py first.")
        sys.exit(1)
    
    latest_equity = equity_files[-1]
    latest_trades = trade_files[-1]
    
    timestamp = latest_equity.stem.split('_')[-1]
    output_file = trades_dir / f'equity_curve_{timestamp}.html'
    
    print("Creating equity curve visualization...")
    fig = create_equity_curve(latest_equity, latest_trades, output_file)
    print("✓ Done!")
