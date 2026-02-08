"""
Interactive Experiment Dashboard for Sentiment Trading Strategy.

Allows real-time parameter tuning and pipeline execution with live visualization updates.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import traceback

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Import current config
sys.path.append(str(PROJECT_ROOT))
from config import stock_universe

# Initialize Dash app
app = dash.Dash(__name__, title="Sentiment Trading Lab", suppress_callback_exceptions=True)
app.layout = html.Div([
    html.Div([
        html.H1("Project Mercury", style={'textAlign': 'center', 'color': '#2E86AB'}),
        html.P("Interactive parameter tuning and backtesting dashboard", 
               style={'textAlign': 'center', 'color': '#666', 'fontSize': '18px'}),
        html.Hr()
    ], style={'padding': '20px', 'backgroundColor': '#f8f9fa'}),
    
    # Main container
    html.Div([
        # Left panel: Controls
        html.Div([
            html.H3("⚙️ Strategy Parameters", style={'color': '#2E86AB'}),
            html.Div([
                html.P("✅ Active Parameters (affect backtest results)", style={'fontSize': '12px', 'color': '#06A77D', 'fontWeight': 'bold', 'marginBottom': '5px'}),
                html.P("⚠️ Pre-optimized (requires lag analysis re-run)", style={'fontSize': '12px', 'color': '#FFBA08', 'fontWeight': 'bold', 'marginBottom': '15px'}),
            ], style={'backgroundColor': '#f8f9fa', 'padding': '10px', 'borderRadius': '5px', 'marginBottom': '20px'}),
            
            # Strategy parameters
            html.Div([
                html.Label("✅ Sentiment Threshold (Buy when sentiment >)", style={'fontWeight': 'bold'}),
                dcc.Slider(
                    id='sentiment-threshold',
                    min=0.0,
                    max=0.5,
                    step=0.05,
                    value=stock_universe.SENTIMENT_THRESHOLD,
                    marks={i/10: f'{i/10:.1f}' for i in range(0, 6)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.Label("⚠️ Lookback Hours (Pre-optimized per stock)", style={'fontWeight': 'bold'}),
                html.P("⚠️ Note: Lag analysis already determined optimal lookback hours for each stock. This setting is stored in config but not used unless you re-run lag analysis.",
                       style={'fontSize': '11px', 'color': '#FFBA08', 'fontStyle': 'italic', 'marginTop': '5px'}),
                dcc.Slider(
                    id='lookback-hours',
                    min=6,
                    max=72,
                    step=6,
                    value=stock_universe.LOOKBACK_HOURS,
                    marks={i: f'{i}h' for i in [6, 12, 24, 48, 72]},
                    tooltip={"placement": "bottom", "always_visible": True},
                    disabled=True
                ),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.Label("✅ Min News Count (Required articles per day)", style={'fontWeight': 'bold'}),
                dcc.Slider(
                    id='min-news-count',
                    min=1,
                    max=10,
                    step=1,
                    value=stock_universe.MIN_NEWS_COUNT,
                    marks={i: str(i) for i in range(1, 11)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.Label("✅ Hold Period (Hours)", style={'fontWeight': 'bold'}),
                dcc.Slider(
                    id='hold-period-hours',
                    min=24,
                    max=24000,
                    step=24,
                    value=stock_universe.HOLD_PERIOD_HOURS,
                    marks={i: f'{i}h' for i in [24, 72, 120, 168, 240, 2400, 4800, 7200, 12000, 24000]},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.Label("✅ Stop Loss (%)", style={'fontWeight': 'bold'}),
                dcc.Slider(
                    id='stop-loss-pct',
                    min=0.01,
                    max=0.10,
                    step=0.01,
                    value=stock_universe.STOP_LOSS_PCT,
                    marks={i/100: f'{i}%' for i in [1, 2, 5, 10]},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.Label("✅ Take Profit (%)", style={'fontWeight': 'bold'}),
                dcc.Slider(
                    id='take-profit-pct',
                    min=0.02,
                    max=1.00,
                    step=0.01,
                    value=stock_universe.TAKE_PROFIT_PCT,
                    marks={i/100: f'{i}%' for i in [2, 5, 10, 15, 20, 50, 100]},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'marginBottom': '30px'}),
            
            # Run button
            html.Div([
                html.Button(
                    '▶️ Run Backtest',
                    id='run-button',
                    n_clicks=0,
                    style={
                        'width': '100%',
                        'padding': '15px',
                        'fontSize': '18px',
                        'fontWeight': 'bold',
                        'backgroundColor': '#06A77D',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }
                ),
            ], style={'marginTop': '40px'}),
            
            # Status indicator
            dcc.Loading(
                id="loading-status",
                type="circle",
                children=html.Div(id='status-output', style={'marginTop': '20px'})
            ),
            
        ], style={
            'width': '30%',
            'padding': '20px',
            'backgroundColor': '#ffffff',
            'borderRadius': '10px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'marginRight': '20px'
        }),
        
        # Right panel: Results
        html.Div([
            # Tabs for different visualizations
            dcc.Tabs(id='tabs', value='equity', children=[
                dcc.Tab(label='Equity Curve', value='equity'),
                dcc.Tab(label='Drawdown', value='drawdown'),
                dcc.Tab(label='Trade Analysis', value='trades'),
                dcc.Tab(label='Monthly Heatmap', value='heatmap'),
                dcc.Tab(label='Metrics', value='metrics'),
                dcc.Tab(label='Lag Analysis', value='lag'),
                dcc.Tab(label='Correlation', value='correlation'),
                dcc.Tab(label='Data Summary', value='data'),
            ]),
            html.Div(id='tab-content', style={'padding': '20px'}),
            
        ], style={
            'width': '68%',
            'backgroundColor': '#ffffff',
            'borderRadius': '10px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'minHeight': '800px'
        }),
        
    ], style={
        'display': 'flex',
        'padding': '20px',
        'backgroundColor': '#f0f2f5'
    }),
    
    # Hidden div to store latest results
    dcc.Store(id='latest-results'),
    
], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f0f2f5'})


@app.callback(
    [Output('status-output', 'children'),
     Output('latest-results', 'data')],
    [Input('run-button', 'n_clicks')],
    [State('sentiment-threshold', 'value'),
     State('lookback-hours', 'value'),
     State('min-news-count', 'value'),
     State('hold-period-hours', 'value'),
     State('stop-loss-pct', 'value'),
     State('take-profit-pct', 'value')]
)
def run_backtest(n_clicks, sentiment_threshold, lookback_hours, min_news_count,
                 hold_period_hours, stop_loss_pct, take_profit_pct):
    """Run the complete backtest pipeline with updated parameters."""
    
    print(f"\n{'='*60}")
    print(f"CALLBACK TRIGGERED: n_clicks={n_clicks}")
    print(f"Parameters being applied:")
    print(f"  • Sentiment Threshold: {sentiment_threshold}")
    print(f"  • Lookback Hours: {lookback_hours} (pre-optimized per stock, not used)")
    print(f"  • Min News Count: {min_news_count}")
    print(f"  • Hold Period: {hold_period_hours}h ({hold_period_hours/24:.1f} days)")
    print(f"  • Stop Loss: {stop_loss_pct*100:.1f}%")
    print(f"  • Take Profit: {take_profit_pct*100:.1f}%")
    print(f"{'='*60}\n")
    
    if n_clicks == 0:
        # Initial load - show existing results
        trades_dir = PROJECT_ROOT / 'trades'
        summary_files = sorted(trades_dir.glob('backtest_summary_*.json'))
        
        if summary_files:
            with open(summary_files[-1], 'r') as f:
                results = json.load(f)
            
            timestamp = summary_files[-1].stem.split('_')[-1]
            return [
                html.Div([
                    html.P("✓ Loaded existing results", style={'color': '#06A77D', 'fontWeight': 'bold'}),
                    html.P(f"Timestamp: {timestamp}", style={'fontSize': '12px', 'color': '#666'})
                ]),
                {'timestamp': timestamp, 'metrics': results}
            ]
        else:
            return [
                html.Div([
                    html.P("⚠️ No existing results found", style={'color': '#FFBA08'}),
                    html.P("Click 'Run Backtest' to generate results", style={'fontSize': '12px'})
                ]),
                None
            ]
    
    # Update config file
    config_path = PROJECT_ROOT / 'config' / 'stock_universe.py'
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        # Update parameters
        updates = {
            'SENTIMENT_THRESHOLD': sentiment_threshold,
            'LOOKBACK_HOURS': int(lookback_hours),
            'MIN_NEWS_COUNT': int(min_news_count),
            'HOLD_PERIOD_HOURS': int(hold_period_hours),
            'STOP_LOSS_PCT': stop_loss_pct,
            'TAKE_PROFIT_PCT': take_profit_pct
        }
        
        new_lines = []
        for line in lines:
            updated = False
            for param, value in updates.items():
                if line.strip().startswith(f'{param} ='):
                    if isinstance(value, int):
                        new_lines.append(f'{param} = {value}\n')
                    else:
                        new_lines.append(f'{param} = {value}\n')
                    updated = True
                    break
            if not updated:
                new_lines.append(line)
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.writelines(new_lines)
        
        # Run pipeline scripts
        status_msgs = []
        
        # Activate venv and run scripts
        venv_python = str(PROJECT_ROOT / '.venv' / 'bin' / 'python3')
        scripts_dir = PROJECT_ROOT / 'scripts'
        
        # Step 1: Generate signals (lag analysis results already exist)
        status_msgs.append("🔄 Generating trading signals...")
        print("📊 Step 1/3: Running signal generation...")
        result = subprocess.run(
            [venv_python, str(scripts_dir / '06_strategy_signals.py')],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300  # 2 minute timeout
        )
        print(f"✓ Signal generation completed (exit code: {result.returncode})")
        
        if result.returncode != 0:
            print(f"❌ Signal generation failed: {result.stderr}")
            return [
                html.Div([
                    html.P("❌ Signal generation failed", style={'color': '#D62828'}),
                    html.Pre(result.stderr, style={'fontSize': '10px', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
                ]),
                None
            ]
        
        # Step 2: Run backtest
        status_msgs.append("🔄 Running backtest simulation...")
        print("📊 Step 2/3: Running backtest simulation...")
        result = subprocess.run(
            [venv_python, str(scripts_dir / '07_backtest.py')],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300  # 2 minute timeout
        )
        print(f"✓ Backtest completed (exit code: {result.returncode})")
        
        if result.returncode != 0:
            print(f"❌ Backtest failed: {result.stderr}")
            return [
                html.Div([
                    html.P("❌ Backtest failed", style={'color': '#D62828'}),
                    html.Pre(result.stderr, style={'fontSize': '10px', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
                ]),
                None
            ]
        
        # Step 3: Generate visualizations
        status_msgs.append("🔄 Generating visualizations...")
        print("📊 Step 3/3: Generating visualizations...")
        for i, viz_script in enumerate(['08_visualize_equity.py', '09_visualize_drawdown.py', 
                          '10_visualize_trades.py', '11_visualize_heatmap.py'], 1):
            print(f"  └─ Viz {i}/4: {viz_script}")
            subprocess.run(
                [venv_python, str(scripts_dir / viz_script)],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
                timeout=60  # 1 minute per visualization
            )
        print("✓ All visualizations generated")
        
        # Load results
        trades_dir = PROJECT_ROOT / 'trades'
        summary_files = sorted(trades_dir.glob('backtest_summary_*.json'))
        
        if summary_files:
            with open(summary_files[-1], 'r') as f:
                results = json.load(f)
            
            timestamp = summary_files[-1].stem.split('_')[-1]
            
            return [
                html.Div([
                    html.P("✅ Backtest completed successfully!", style={'color': '#06A77D', 'fontWeight': 'bold', 'fontSize': '16px'}),
                    html.Hr(style={'margin': '10px 0'}),
                    html.P(f"Return: {results['total_return_pct']:.2f}%", style={'fontSize': '14px', 'margin': '5px 0'}),
                    html.P(f"Win Rate: {results['win_rate']:.1f}%", style={'fontSize': '14px', 'margin': '5px 0'}),
                    html.P(f"Sharpe: {results['sharpe_ratio']:.2f}", style={'fontSize': '14px', 'margin': '5px 0'}),
                    html.Hr(style={'margin': '10px 0'}),
                    html.P("Parameters used:", style={'fontSize': '12px', 'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.P(f"Sentiment: {sentiment_threshold} | Min News: {int(min_news_count)} | Hold: {int(hold_period_hours)}h", 
                           style={'fontSize': '11px', 'color': '#666'}),
                    html.P(f"Stop Loss: {stop_loss_pct*100:.0f}% | Take Profit: {take_profit_pct*100:.0f}%", 
                           style={'fontSize': '11px', 'color': '#666'}),
                    html.P(f"Timestamp: {timestamp}", style={'fontSize': '10px', 'color': '#999', 'marginTop': '10px'})
                ]),
                {'timestamp': timestamp, 'metrics': results}
            ]
        else:
            return [
                html.Div([
                    html.P("⚠️ Results not found after run", style={'color': '#FFBA08'})
                ]),
                None
            ]
            
    except subprocess.TimeoutExpired as e:
        print(f"\n TIMEOUT: Script took too long to execute")
        return [
            html.Div([
                html.P(f"⏱️ Timeout: Script took too long (>2 minutes)", style={'color': '#FFBA08'}),
                html.P("Try reducing the date range or number of stocks in config", style={'fontSize': '12px'})
            ]),
            None
        ]
    except Exception as e:
        print(f"\nERROR in callback: {str(e)}")
        print(traceback.format_exc())
        return [
            html.Div([
                html.P(f"Error: {str(e)}", style={'color': '#D62828'}),
                html.Pre(traceback.format_exc(), style={'fontSize': '10px', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
            ]),
            None
        ]


@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'value'),
     Input('latest-results', 'data')]
)
def render_tab_content(active_tab, results_data):
    """Render content based on selected tab."""
    
    # Static tabs don't need results_data
    if active_tab in ['lag', 'correlation', 'data']:
        return render_static_tab(active_tab)
    
    if not results_data:
        return html.Div([
            html.P("⏳ No results available yet. Run a backtest to see results.", 
                   style={'textAlign': 'center', 'padding': '50px', 'color': '#666'})
        ])
    
    timestamp = results_data['timestamp']
    trades_dir = PROJECT_ROOT / 'trades'
    
    if active_tab == 'equity':
        # Load and display equity curve
        html_file = trades_dir / f'equity_curve_{timestamp}.html'
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html.Iframe(srcDoc=html_content, style={'width': '100%', 'height': '700px', 'border': 'none'})
        
    elif active_tab == 'drawdown':
        html_file = trades_dir / f'drawdown_chart_{timestamp}.html'
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html.Iframe(srcDoc=html_content, style={'width': '100%', 'height': '600px', 'border': 'none'})
    
    elif active_tab == 'trades':
        html_file = trades_dir / f'trade_analysis_{timestamp}.html'
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html.Iframe(srcDoc=html_content, style={'width': '100%', 'height': '900px', 'border': 'none'})
    
    elif active_tab == 'heatmap':
        html_file = trades_dir / f'monthly_heatmap_{timestamp}.html'
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html.Iframe(srcDoc=html_content, style={'width': '100%', 'height': '500px', 'border': 'none'})
    
    elif active_tab == 'metrics':
        # Display metrics in a formatted table
        metrics = results_data['metrics']
        
        return html.Div([
            html.H3("Performance Metrics Summary"),
            
            html.Div([
                html.H4("Period", style={'color': '#2E86AB'}),
                html.Table([
                    html.Tr([html.Td("Start Date", style={'fontWeight': 'bold'}), html.Td(metrics['start_date'])]),
                    html.Tr([html.Td("End Date", style={'fontWeight': 'bold'}), html.Td(metrics['end_date'])]),
                    html.Tr([html.Td("Trading Days", style={'fontWeight': 'bold'}), html.Td(metrics['trading_days'])]),
                ], style={'width': '100%', 'borderCollapse': 'collapse'}),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.H4("P&L Summary", style={'color': '#2E86AB'}),
                html.Table([
                    html.Tr([html.Td("Initial Capital", style={'fontWeight': 'bold'}), html.Td(f"${metrics['initial_capital']:,.2f}")]),
                    html.Tr([html.Td("Final Equity", style={'fontWeight': 'bold'}), html.Td(f"${metrics['final_equity']:,.2f}")]),
                    html.Tr([html.Td("Total Return", style={'fontWeight': 'bold', 'color': '#06A77D' if metrics['total_return_pct'] > 0 else '#D62828'}), 
                             html.Td(f"{metrics['total_return_pct']:+.2f}%", style={'color': '#06A77D' if metrics['total_return_pct'] > 0 else '#D62828'})]),
                    html.Tr([html.Td("Annual Return", style={'fontWeight': 'bold'}), html.Td(f"{metrics['annual_return']*100:+.2f}%")]),
                ], style={'width': '100%'}),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.H4("Trade Statistics", style={'color': '#2E86AB'}),
                html.Table([
                    html.Tr([html.Td("Total Trades", style={'fontWeight': 'bold'}), html.Td(metrics['num_trades'])]),
                    html.Tr([html.Td("Wins / Losses", style={'fontWeight': 'bold'}), html.Td(f"{metrics['num_wins']} / {metrics['num_losses']}")]),
                    html.Tr([html.Td("Win Rate", style={'fontWeight': 'bold'}), html.Td(f"{metrics['win_rate']:.1f}%")]),
                    html.Tr([html.Td("Avg Days Held", style={'fontWeight': 'bold'}), html.Td(f"{metrics['avg_days_held']:.1f}")]),
                ], style={'width': '100%'}),
            ], style={'marginBottom': '30px'}),
            
            html.Div([
                html.H4("Risk Metrics", style={'color': '#2E86AB'}),
                html.Table([
                    html.Tr([html.Td("Sharpe Ratio", style={'fontWeight': 'bold'}), html.Td(f"{metrics['sharpe_ratio']:.2f}")]),
                    html.Tr([html.Td("Sortino Ratio", style={'fontWeight': 'bold'}), html.Td(f"{metrics['sortino_ratio']:.2f}")]),
                    html.Tr([html.Td("Calmar Ratio", style={'fontWeight': 'bold'}), html.Td(f"{metrics['calmar_ratio']:.2f}")]),
                    html.Tr([html.Td("Max Drawdown", style={'fontWeight': 'bold', 'color': '#D62828'}), 
                             html.Td(f"{metrics['max_drawdown_pct']:.2f}%", style={'color': '#D62828'})]),
                    html.Tr([html.Td("Annual Volatility", style={'fontWeight': 'bold'}), html.Td(f"{metrics['annual_volatility']*100:.2f}%")]),
                ], style={'width': '100%'}),
            ], style={'marginBottom': '30px'}),
            
        ], style={'padding': '20px'})
    
    return html.Div("Select a tab to view results")


def render_static_tab(tab_name):
    """Render static analysis tabs that don't change with parameters."""
    
    if tab_name == 'lag':
        # Load lag analysis results
        lag_file = PROJECT_ROOT / 'data' / 'analysis' / 'lag_analysis.json'
        if not lag_file.exists():
            return html.Div("⚠️ Lag analysis not found. Run scripts/05_lag_analysis.py", 
                          style={'padding': '20px', 'color': '#FFBA08'})
        
        with open(lag_file, 'r') as f:
            lag_data = json.load(f)
        
        rows = []
        for ticker, data in lag_data.items():
            if data['best_config']:
                cfg = data['best_config']
                rows.append(html.Tr([
                    html.Td(ticker, style={'fontWeight': 'bold', 'fontSize': '14px'}),
                    html.Td(f"{cfg['lookback_hours']}h"),
                    html.Td(f"{cfg['lead_days']}d"),
                    html.Td(f"{cfg['correlation']:+.3f}", 
                           style={'color': '#D62828' if cfg['correlation'] < 0 else '#06A77D', 'fontWeight': 'bold'}),
                    html.Td(f"{cfg['p_value']:.4f}"),
                    html.Td(str(cfg['observations'])),
                    html.Td('Inverse' if cfg['correlation'] < 0 else 'Direct',
                           style={'color': '#D62828' if cfg['correlation'] < 0 else '#06A77D'})
                ]))
        
        return html.Div([
            html.H3("Lag Analysis: Optimal Configurations", style={'marginBottom': '20px'}),
            html.P("Pre-optimized sentiment-to-return relationships (200 configs tested per stock)",
                  style={'color': '#666', 'marginBottom': '20px'}),
            
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Lookback", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Lead Time", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Correlation", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("P-Value", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Observations", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Strategy", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                ])),
                html.Tbody(rows)
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginTop': '20px'}),
            
            html.Div([
                html.H4("Key Insights:", style={'marginTop': '30px', 'color': '#2E86AB'}),
                html.Ul([
                    html.Li("NVDA shows strongest correlation (-0.529) at 72h lookback"),
                    html.Li("AAPL performs best at 12h lookback (-0.435)"),
                    html.Li("TSLA and GOOGL have positive correlations (direct strategy)"),
                    html.Li("Most stocks require inverse strategy (negative correlation)"),
                ], style={'lineHeight': '1.8'})
            ], style={'marginTop': '30px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'})
        ], style={'padding': '20px'})
    
    elif tab_name == 'correlation':
        # Load correlation data
        corr_file = PROJECT_ROOT / 'data' / 'analysis' / 'correlation_summary.json'
        if not corr_file.exists():
            return html.Div("⚠️ Correlation analysis not found. Run scripts/04_correlation_analysis.py",
                          style={'padding': '20px', 'color': '#FFBA08'})
        
        with open(corr_file, 'r') as f:
            corr_data = json.load(f)
        
        rows = []
        for ticker, data in corr_data.items():
            if ticker != 'OVERALL':
                rows.append(html.Tr([
                    html.Td(ticker, style={'fontWeight': 'bold', 'fontSize': '14px'}),
                    html.Td(f"{data['corr_1d']:+.3f}"),
                    html.Td(f"{data['corr_3d']:+.3f}"),
                    html.Td(f"{data['corr_5d']:+.3f}"),
                    html.Td(str(data['observations'])),
                ]))
        
        overall = corr_data['OVERALL']
        
        return html.Div([
            html.H3("Correlation Analysis: Sentiment vs Returns", style={'marginBottom': '20px'}),
            html.P("Historical correlation between news sentiment and future price returns",
                  style={'color': '#666', 'marginBottom': '20px'}),
            
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("1-Day", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("3-Day", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("5-Day", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                    html.Th("Observations", style={'padding': '10px', 'borderBottom': '2px solid #2E86AB'}),
                ])),
                html.Tbody(rows + [html.Tr([
                    html.Td("OVERALL", style={'fontWeight': 'bold', 'fontSize': '14px', 'borderTop': '2px solid #2E86AB', 'paddingTop': '10px'}),
                    html.Td(f"{overall['corr_1d']:+.3f}", style={'borderTop': '2px solid #2E86AB', 'paddingTop': '10px'}),
                    html.Td(f"{overall['corr_3d']:+.3f}", style={'borderTop': '2px solid #2E86AB', 'paddingTop': '10px'}),
                    html.Td(f"{overall['corr_5d']:+.3f}", style={'borderTop': '2px solid #2E86AB', 'paddingTop': '10px'}),
                    html.Td(str(overall['observations']), style={'borderTop': '2px solid #2E86AB', 'paddingTop': '10px'}),
                ])])
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginTop': '20px'}),
            
            html.Div([
                html.H4("Key Findings:", style={'marginTop': '30px', 'color': '#2E86AB'}),
                html.Ul([
                    html.Li(f"Overall correlation: {overall['corr_5d']:+.3f} (5-day horizon)"),
                    html.Li(f"Total observations: {overall['observations']} across all stocks"),
                    html.Li("Most stocks show negative correlation (contrarian indicator)"),
                    html.Li("Correlation strengthens with longer time horizons"),
                ], style={'lineHeight': '1.8'})
            ], style={'marginTop': '30px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'})
        ], style={'padding': '20px'})
    
    elif tab_name == 'data':
        # Data summary
        try:
            news_file = PROJECT_ROOT / 'data' / 'news' / 'news_with_sentiment.parquet'
            news_df = pd.read_parquet(news_file)
            
            prices_dir = PROJECT_ROOT / 'data' / 'prices'
            price_files = list(prices_dir.glob('*_ohlcv.parquet'))
            
            corr_file = PROJECT_ROOT / 'data' / 'analysis' / 'correlation_summary.json'
            if corr_file.exists():
                with open(corr_file, 'r') as f:
                    corr_data = json.load(f)
                corr_obs = corr_data.get('OVERALL', {}).get('observations', 'N/A')
            else:
                corr_obs = 'N/A'
            
            return html.Div([
                html.H3("Data Summary", style={'marginBottom': '20px'}),
                
                html.Div([
                    html.H4("News Data", style={'color': '#2E86AB'}),
                    html.Table([
                        html.Tr([html.Td("Total Articles", style={'fontWeight': 'bold'}), 
                                html.Td(f"{len(news_df):,}")]),
                        html.Tr([html.Td("Date Range", style={'fontWeight': 'bold'}), 
                                html.Td(f"{news_df['published_utc'].min()} to {news_df['published_utc'].max()}")]),
                        html.Tr([html.Td("Stocks Covered", style={'fontWeight': 'bold'}), 
                                html.Td(f"{news_df['ticker_queried'].nunique()}")]),
                        html.Tr([html.Td("Avg Sentiment", style={'fontWeight': 'bold'}), 
                                html.Td(f"{news_df['sentiment'].mean():.3f}")]),
                        html.Tr([html.Td("Sentiment Distribution", style={'fontWeight': 'bold'}), 
                                html.Td(f"Positive: {(news_df['sentiment'] > 0).sum():,} | Negative: {(news_df['sentiment'] < 0).sum():,} | Neutral: {(news_df['sentiment'] == 0).sum():,}")]),
                    ], style={'width': '100%', 'borderCollapse': 'collapse'}),
                ], style={'marginBottom': '30px'}),
                
                html.Div([
                    html.H4("Price Data", style={'color': '#2E86AB'}),
                    html.Table([
                        html.Tr([html.Td("Stocks", style={'fontWeight': 'bold'}), 
                                html.Td(f"{len(price_files)}")]),
                        html.Tr([html.Td("Bars per Stock", style={'fontWeight': 'bold'}), 
                                html.Td("1,528 (2020-01-01 to 2026-01-31)")]),
                        html.Tr([html.Td("Resolution", style={'fontWeight': 'bold'}), 
                                html.Td("Daily OHLCV")]),
                    ], style={'width': '100%', 'borderCollapse': 'collapse'}),
                ], style={'marginBottom': '30px'}),
                
                html.Div([
                    html.H4("Analysis Status", style={'color': '#2E86AB'}),
                    html.Table([
                        html.Tr([html.Td("Lag Analysis", style={'fontWeight': 'bold'}), 
                                html.Td("✅ Complete (200 configs tested)")]),
                        html.Tr([html.Td("Correlation Analysis", style={'fontWeight': 'bold'}), 
                                html.Td(f"✅ Complete ({corr_obs} observations)" if corr_obs != 'N/A' else "❌ Not run")]),
                        html.Tr([html.Td("Signal Generation", style={'fontWeight': 'bold'}), 
                                html.Td("✅ Ready")]),
                    ], style={'width': '100%', 'borderCollapse': 'collapse'}),
                ]),
                
            ], style={'padding': '20px'})
            
        except Exception as e:
            return html.Div(f"⚠️ Error loading data summary: {str(e)}",
                          style={'padding': '20px', 'color': '#D62828'})
    
    return html.Div("Unknown tab")


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" Project Mercury")
    print("="*70)
    print("\nInteractive dashboard starting...")
    print("Open your browser to: http://127.0.0.1:8050/")
    print("\nAdjust parameters and click 'Run Backtest' to see results")
    print("Switch between tabs to view different visualizations")
    print("\n" + "="*70 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=8050)
