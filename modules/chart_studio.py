import json
import streamlit as st
import streamlit.components.v1 as components


def render_kline_chart(df, symbol_name="NSE Stock", height=600):
    """Renders a dark-themed KLineChart with full drawing tools (trendlines, rays, horizontal lines)
    using standard OHLCV dataframe input.
    """
    if df is None or df.empty:
        st.warning(f"No chart data available to render for {symbol_name}.")
        return

    # Prepare candle data formatted for KLineChart
    df_clean = df.copy()
    if not isinstance(df_clean.index, (st.session_state.__class__,)):
        df_clean = df_clean.reset_index()

    # Find the datetime column
    date_col = None
    for c in ["Date", "Datetime", "index", "timestamp"]:
        if c in df_clean.columns:
            date_col = c
            break

    if date_col is None:
        date_col = df_clean.columns[0]

    chart_data = []
    for _, row in df_clean.iterrows():
        try:
            dt_val = row[date_col]
            # Convert to millisecond timestamp
            ts = int(dt_val.timestamp() * 1000) if hasattr(dt_val, "timestamp") else int(row.name * 1000)
            chart_data.append(
                {
                    "timestamp": ts,
                    "open": float(row.get("Open", row.get("open", 0))),
                    "high": float(row.get("High", row.get("high", 0))),
                    "low": float(row.get("Low", row.get("low", 0))),
                    "close": float(row.get("Close", row.get("close", 0))),
                    "volume": float(row.get("Volume", row.get("volume", 0))),
                }
            )
        except Exception:
            continue

    data_json = json.dumps(chart_data)

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://unpkg.com/klinecharts/dist/klinecharts.min.js"></script>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background-color: #131722;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                overflow: hidden;
            }}
            #toolbar {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                background-color: #1e222d;
                border-bottom: 1px solid #2a2e39;
            }}
            .tool-btn {{
                background-color: #2a2e39;
                color: #d1d4dc;
                border: 1px solid #363c4e;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .tool-btn:hover {{
                background-color: #2962ff;
                color: #ffffff;
                border-color: #2962ff;
            }}
            .stock-title {{
                color: #f0b90b;
                font-size: 14px;
                font-weight: 600;
                margin-right: 12px;
            }}
            #chart-container {{
                width: 100%;
                height: calc(100% - 45px);
            }}
        </style>
    </head>
    <body>
        <div id="toolbar">
            <span class="stock-title">📊 {symbol_name} (30m Intraday)</span>
            <button class="tool-btn" onclick="setOverlay('segment')">📏 Trendline</button>
            <button class="tool-btn" onclick="setOverlay('rayLine')">↗️ Ray Line</button>
            <button class="tool-btn" onclick="setOverlay('horizontalRayLine')">⎯ Horizontal Level</button>
            <button class="tool-btn" onclick="setOverlay('fibonacci')">🌀 Fibonacci</button>
            <button class="tool-btn" onclick="clearOverlays()" style="margin-left: auto; background-color: #8b0000; border-color: #a00000;">🗑️ Clear Tools</button>
        </div>
        <div id="chart-container"></div>

        <script>
            const chart = klinecharts.init('chart-container', {{
                grid: {{
                    show: true,
                    horizontal: {{ color: '#1f232f' }},
                    vertical: {{ color: '#1f232f' }}
                }},
                candle: {{
                    type: 'candle_solid',
                    bar: {{
                        upColor: '#089981',
                        downColor: '#f23645',
                        upBorderColor: '#089981',
                        downBorderColor: '#f23645',
                        upWickColor: '#089981',
                        downWickColor: '#f23645'
                    }}
                }}
            }});

            const klineData = {data_json};
            chart.applyNewData(klineData);
            chart.createIndicator('VOL', false, {{ height: 80 }});
            chart.createIndicator('EMA', true, {{ params: [10, 21, 50] }});

            function setOverlay(name) {{
                chart.createOverlay(name);
            }}

            function clearOverlays() {{
                chart.removeOverlay();
            }}
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=height)
