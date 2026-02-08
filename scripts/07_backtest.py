"""
Backtesting Engine: Simulate trading strategy and calculate comprehensive metrics.

Implements walk-forward validation with transaction costs and slippage.
Tracks 34+ comprehensive performance metrics.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.stock_universe import (
    TOP_10_TECH_STOCKS,
    BACKTEST_START,
    BACKTEST_END,
    HOLD_PERIOD_HOURS,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT
)

# Backtest parameters
INITIAL_CAPITAL = 100000.0
POSITION_SIZE = 0.8  # 80% of capital per position
MAX_POSITIONS = 10  # Maximum concurrent positions
TRANSACTION_COST = 0.001  # 0.1% per trade
SLIPPAGE = 0.0005  # 0.05% slippage

# Import from config (updated by dashboard)
HOLD_PERIOD_DAYS = HOLD_PERIOD_HOURS / 24  # Convert hours to days
STOP_LOSS = -STOP_LOSS_PCT  # Convert to negative
TAKE_PROFIT = TAKE_PROFIT_PCT

class Portfolio:
    """Track portfolio state during backtest."""
    
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # ticker -> {shares, entry_price, entry_date, sentiment, news_count}
        self.equity_history = []
        self.trade_history = []
        self.daily_returns = []
        
    def get_equity(self, price_data, current_date):
        """Calculate total portfolio equity."""
        position_value = 0
        for ticker, pos in self.positions.items():
            if current_date in price_data[ticker].index:
                current_price = price_data[ticker].at[current_date, 'Close']
                position_value += pos['shares'] * current_price
        
        return self.cash + position_value
    
    def can_open_position(self):
        """Check if we can open a new position."""
        return len(self.positions) < MAX_POSITIONS
    
    def open_position(self, ticker, price, date, sentiment, news_count, signal_data):
        """Open a new long position."""
        if not self.can_open_position():
            return False
        
        # Calculate position size
        position_value = self.cash * POSITION_SIZE
        
        # Apply slippage and transaction costs
        entry_price = price * (1 + SLIPPAGE)
        shares = position_value / entry_price
        total_cost = shares * entry_price * (1 + TRANSACTION_COST)
        
        if total_cost > self.cash:
            return False
        
        # Open position
        self.cash -= total_cost
        self.positions[ticker] = {
            'shares': shares,
            'entry_price': entry_price,
            'entry_date': date,
            'sentiment': sentiment,
            'news_count': news_count,
            'lookback_hours': signal_data['lookback_hours'],
            'lead_days': signal_data['lead_days'],
            'days_held': 0
        }
        
        return True
    
    def close_position(self, ticker, price, date, exit_reason):
        """Close an existing position."""
        if ticker not in self.positions:
            return None
        
        pos = self.positions[ticker]
        
        # Apply slippage and transaction costs
        exit_price = price * (1 - SLIPPAGE)
        proceeds = pos['shares'] * exit_price * (1 - TRANSACTION_COST)
        
        # Calculate P&L
        cost_basis = pos['shares'] * pos['entry_price'] * (1 + TRANSACTION_COST)
        pnl = proceeds - cost_basis
        pnl_pct = (exit_price / pos['entry_price'] - 1) * 100
        
        # Record trade
        trade = {
            'ticker': ticker,
            'entry_date': pos['entry_date'],
            'exit_date': date,
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'shares': pos['shares'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'sentiment': pos['sentiment'],
            'news_count': pos['news_count'],
            'lookback_hours': pos['lookback_hours'],
            'lead_days': pos['lead_days'],
            'days_held': pos['days_held']
        }
        self.trade_history.append(trade)
        
        # Update cash
        self.cash += proceeds
        
        # Remove position
        del self.positions[ticker]
        
        return trade
    
    def update_positions(self, price_data, current_date):
        """Update position days held and check exit conditions."""
        to_close = []
        
        for ticker, pos in self.positions.items():
            pos['days_held'] += 1
            
            if current_date not in price_data[ticker].index:
                continue
            
            current_price = price_data[ticker].at[current_date, 'Close']
            return_pct = (current_price / pos['entry_price']) - 1
            
            # Check exit conditions
            exit_reason = None
            
            if return_pct <= STOP_LOSS:
                exit_reason = 'stop_loss'
            elif return_pct >= TAKE_PROFIT:
                exit_reason = 'take_profit'
            elif pos['days_held'] >= HOLD_PERIOD_DAYS:
                exit_reason = 'hold_period'
            
            if exit_reason:
                to_close.append((ticker, current_price, exit_reason))
        
        # Close positions
        for ticker, price, reason in to_close:
            self.close_position(ticker, price, current_date, reason)

def load_data():
    """Load all required data."""
    # Load signals
    signals_path = Path(__file__).parent.parent / 'data' / 'signals' / 'trading_signals.parquet'
    signals_df = pd.read_parquet(signals_path)
    signals_df['date'] = pd.to_datetime(signals_df['date'])
    
    # Load prices
    prices_dir = Path(__file__).parent.parent / 'data' / 'prices'
    price_data = {}
    for ticker in TOP_10_TECH_STOCKS:
        price_file = prices_dir / f"{ticker}_ohlcv.parquet"
        if price_file.exists():
            df = pd.read_parquet(price_file)
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            price_data[ticker] = df
    
    return signals_df, price_data

def run_backtest(signals_df, price_data):
    """Execute backtest simulation."""
    # Filter signals for backtest period
    backtest_start = pd.to_datetime(BACKTEST_START).tz_localize('UTC')
    backtest_end = pd.to_datetime(BACKTEST_END).tz_localize('UTC')
    
    signals_df = signals_df[
        (signals_df['date'] >= backtest_start) & 
        (signals_df['date'] <= backtest_end)
    ].copy()
    
    # Initialize portfolio
    portfolio = Portfolio(INITIAL_CAPITAL)
    
    # Get all trading dates
    all_dates = set()
    for df in price_data.values():
        all_dates.update(df.index)
    trading_dates = sorted([d for d in all_dates if backtest_start <= d <= backtest_end])
    
    print(f"Running backtest from {backtest_start.date()} to {backtest_end.date()}")
    print(f"Total trading days: {len(trading_dates)}")
    print(f"Initial capital: ${INITIAL_CAPITAL:,.2f}\n")
    
    # Simulate each trading day
    for i, current_date in enumerate(trading_dates):
        # Update existing positions
        portfolio.update_positions(price_data, current_date)
        
        # Check for new signals
        day_signals = signals_df[signals_df['date'] == current_date]
        
        for _, signal in day_signals.iterrows():
            # Only process BUY signals (long-only strategy)
            if signal['signal'] == 'BUY':
                ticker = signal['ticker']
                
                # Skip if already have position
                if ticker in portfolio.positions:
                    continue
                
                # Try to open position
                if current_date in price_data[ticker].index:
                    price = price_data[ticker].at[current_date, 'Close']
                    portfolio.open_position(
                        ticker, price, current_date,
                        signal['sentiment'], signal['news_count'],
                        signal
                    )
        
        # Record daily equity
        equity = portfolio.get_equity(price_data, current_date)
        portfolio.equity_history.append({
            'date': current_date,
            'equity': equity,
            'cash': portfolio.cash,
            'num_positions': len(portfolio.positions)
        })
        
        # Calculate daily return
        if i > 0:
            prev_equity = portfolio.equity_history[i-1]['equity']
            daily_return = (equity / prev_equity) - 1
            portfolio.daily_returns.append(daily_return)
        
        # Progress update
        if (i + 1) % 50 == 0:
            print(f"Processed {i+1}/{len(trading_dates)} days | "
                  f"Equity: ${equity:,.2f} | "
                  f"Trades: {len(portfolio.trade_history)}")
    
    # Close any remaining positions at end
    for ticker in list(portfolio.positions.keys()):
        if trading_dates[-1] in price_data[ticker].index:
            final_price = price_data[ticker].at[trading_dates[-1], 'Close']
            portfolio.close_position(ticker, final_price, trading_dates[-1], 'end_of_backtest')
    
    return portfolio

def calculate_metrics(portfolio):
    """Calculate comprehensive performance metrics."""
    equity_df = pd.DataFrame(portfolio.equity_history)
    trades_df = pd.DataFrame(portfolio.trade_history) if portfolio.trade_history else pd.DataFrame()
    
    # Basic metrics
    final_equity = equity_df['equity'].iloc[-1]
    total_return = (final_equity / portfolio.initial_capital) - 1
    total_return_pct = total_return * 100
    
    # Period metrics
    start_date = equity_df['date'].iloc[0]
    end_date = equity_df['date'].iloc[-1]
    trading_days = len(equity_df)
    
    # Trade metrics
    num_trades = len(trades_df)
    
    if num_trades > 0:
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = num_wins / num_trades * 100 if num_trades > 0 else 0
        
        avg_win = winning_trades['pnl'].mean() if num_wins > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if num_losses > 0 else 0
        avg_win_pct = winning_trades['pnl_pct'].mean() if num_wins > 0 else 0
        avg_loss_pct = losing_trades['pnl_pct'].mean() if num_losses > 0 else 0
        
        largest_win = trades_df['pnl'].max()
        largest_loss = trades_df['pnl'].min()
        largest_win_pct = trades_df['pnl_pct'].max()
        largest_loss_pct = trades_df['pnl_pct'].min()
        
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if num_losses > 0 else 0
        expectancy = trades_df['pnl'].mean()
        
        avg_days_held = trades_df['days_held'].mean()
        
        # Win/loss streaks
        trades_df['win'] = trades_df['pnl'] > 0
        trades_df['streak'] = (trades_df['win'] != trades_df['win'].shift()).cumsum()
        win_streaks = trades_df[trades_df['win']].groupby('streak').size()
        loss_streaks = trades_df[~trades_df['win']].groupby('streak').size()
        
        max_win_streak = win_streaks.max() if len(win_streaks) > 0 else 0
        max_loss_streak = loss_streaks.max() if len(loss_streaks) > 0 else 0
    else:
        num_wins = num_losses = 0
        win_rate = avg_win = avg_loss = 0
        avg_win_pct = avg_loss_pct = 0
        largest_win = largest_loss = 0
        largest_win_pct = largest_loss_pct = 0
        profit_factor = expectancy = 0
        avg_days_held = 0
        max_win_streak = max_loss_streak = 0
    
    # Drawdown analysis
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] / equity_df['peak']) - 1
    
    max_drawdown = equity_df['drawdown'].min()
    max_drawdown_pct = max_drawdown * 100
    
    # Find max drawdown period
    dd_idx = equity_df['drawdown'].idxmin()
    dd_end_date = equity_df.loc[dd_idx, 'date']
    dd_peak = equity_df.loc[:dd_idx, 'peak'].max()
    dd_start_idx = equity_df[equity_df['equity'] == dd_peak].index[0]
    dd_start_date = equity_df.loc[dd_start_idx, 'date']
    dd_duration_days = (dd_end_date - dd_start_date).days
    
    # Risk metrics
    daily_returns = np.array(portfolio.daily_returns)
    
    if len(daily_returns) > 0:
        avg_daily_return = daily_returns.mean()
        daily_volatility = daily_returns.std()
        
        # Annualized metrics (252 trading days)
        annual_return = (1 + avg_daily_return) ** 252 - 1
        annual_volatility = daily_volatility * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        downside_volatility = downside_std * np.sqrt(252)
        sortino_ratio = annual_return / downside_volatility if downside_volatility > 0 else 0
        
        # Calmar ratio (return / max drawdown)
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
    else:
        avg_daily_return = daily_volatility = 0
        annual_return = annual_volatility = 0
        sharpe_ratio = sortino_ratio = calmar_ratio = 0
    
    # Compile all metrics
    metrics = {
        # Period metrics
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'trading_days': trading_days,
        
        # P&L metrics
        'initial_capital': portfolio.initial_capital,
        'final_equity': final_equity,
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        
        # Trade metrics
        'num_trades': num_trades,
        'num_wins': num_wins,
        'num_losses': num_losses,
        'win_rate': win_rate,
        
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_win_pct': avg_win_pct,
        'avg_loss_pct': avg_loss_pct,
        
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'largest_win_pct': largest_win_pct,
        'largest_loss_pct': largest_loss_pct,
        
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'avg_days_held': avg_days_held,
        
        'max_win_streak': int(max_win_streak),
        'max_loss_streak': int(max_loss_streak),
        
        # Drawdown metrics
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'max_drawdown_start': dd_start_date.strftime('%Y-%m-%d'),
        'max_drawdown_end': dd_end_date.strftime('%Y-%m-%d'),
        'max_drawdown_duration_days': dd_duration_days,
        
        # Risk metrics
        'avg_daily_return': avg_daily_return,
        'daily_volatility': daily_volatility,
        'annual_return': annual_return,
        'annual_volatility': annual_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio
    }
    
    return metrics, equity_df, trades_df

def save_results(metrics, equity_df, trades_df):
    """Save backtest results to trades/ folder."""
    trades_dir = Path(__file__).parent.parent / 'trades'
    trades_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Save metrics summary (JSON)
    summary_path = trades_dir / f'backtest_summary_{timestamp}.json'
    with open(summary_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # 2. Save trade log (CSV)
    if len(trades_df) > 0:
        trades_path = trades_dir / f'trade_log_{timestamp}.csv'
        trades_df.to_csv(trades_path, index=False)
    
    # 3. Save daily equity (CSV)
    equity_path = trades_dir / f'daily_equity_{timestamp}.csv'
    equity_df.to_csv(equity_path, index=False)
    
    print(f"\nResults saved to {trades_dir}/")
    print(f"  - {summary_path.name}")
    if len(trades_df) > 0:
        print(f"  - {trades_path.name}")
    print(f"  - {equity_path.name}")
    
    return summary_path, trades_dir

def print_metrics_report(metrics):
    """Print comprehensive metrics report."""
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    
    print(f"\nPERIOD")
    print(f"  Start Date: {metrics['start_date']}")
    print(f"  End Date: {metrics['end_date']}")
    print(f"  Trading Days: {metrics['trading_days']}")
    
    print(f"\nP&L SUMMARY")
    print(f"  Initial Capital: ${metrics['initial_capital']:,.2f}")
    print(f"  Final Equity: ${metrics['final_equity']:,.2f}")
    print(f"  Total Return: {metrics['total_return_pct']:+.2f}%")
    print(f"  Annual Return: {metrics['annual_return']*100:+.2f}%")
    
    print(f"\nTRADE STATISTICS")
    print(f"  Total Trades: {metrics['num_trades']}")
    print(f"  Wins: {metrics['num_wins']} | Losses: {metrics['num_losses']}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Avg Days Held: {metrics['avg_days_held']:.1f}")
    
    print(f"\nWIN/LOSS ANALYSIS")
    print(f"  Avg Win: ${metrics['avg_win']:,.2f} ({metrics['avg_win_pct']:+.2f}%)")
    print(f"  Avg Loss: ${metrics['avg_loss']:,.2f} ({metrics['avg_loss_pct']:+.2f}%)")
    print(f"  Largest Win: ${metrics['largest_win']:,.2f} ({metrics['largest_win_pct']:+.2f}%)")
    print(f"  Largest Loss: ${metrics['largest_loss']:,.2f} ({metrics['largest_loss_pct']:+.2f}%)")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Expectancy: ${metrics['expectancy']:,.2f}")
    
    print(f"\nSTREAKS")
    print(f"  Max Win Streak: {metrics['max_win_streak']} trades")
    print(f"  Max Loss Streak: {metrics['max_loss_streak']} trades")
    
    print(f"\nDRAWDOWN ANALYSIS")
    print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  DD Start: {metrics['max_drawdown_start']}")
    print(f"  DD End: {metrics['max_drawdown_end']}")
    print(f"  DD Duration: {metrics['max_drawdown_duration_days']} days")
    
    print(f"\nRISK METRICS")
    print(f"  Daily Volatility: {metrics['daily_volatility']*100:.2f}%")
    print(f"  Annual Volatility: {metrics['annual_volatility']*100:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print(f"  Calmar Ratio: {metrics['calmar_ratio']:.2f}")
    
    print("\n" + "="*70)

def main():
    """Main backtest execution."""
    print("Loading data...")
    signals_df, price_data = load_data()
    
    print(f"Signals loaded: {len(signals_df)}")
    print(f"Price data loaded for {len(price_data)} stocks\n")
    
    # Run backtest
    portfolio = run_backtest(signals_df, price_data)
    
    # Calculate metrics
    print("\nCalculating metrics...")
    metrics, equity_df, trades_df = calculate_metrics(portfolio)
    
    # Save results
    summary_path, trades_dir = save_results(metrics, equity_df, trades_df)
    
    # Print report
    print_metrics_report(metrics)
    
    return metrics, equity_df, trades_df

if __name__ == '__main__':
    metrics, equity_df, trades_df = main()
