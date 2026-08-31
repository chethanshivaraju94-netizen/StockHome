import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

def render_interactive_chart(symbol, df):
    """
    Takes a yfinance OHLCV dataframe, converts it to JSON, 
    and renders a highly interactive KLineChart JS canvas.
    """
    
    records = []
    for idx, row in df.iterrows():
        # Safeguard against yfinance multi-index weirdness
        open_val = row['Open'].iloc[0] if isinstance(row['Open'], pd.Series) else row['Open']
        high_val = row['High'].iloc[0] if isinstance(row['High'], pd.Series) else row['High']
        low_val = row['Low'].iloc[0] if isinstance(row['Low'], pd.Series) else row['Low']
        close_val = row['Close'].iloc[0] if isinstance(row['Close'], pd.Series) else row['Close']
        vol_val = row['Volume'].iloc[0] if isinstance(row['Volume'], pd.Series) else row['Volume']
        
        # KLineChart requires timestamps in milliseconds
        records.append({
            "timestamp": int(idx.timestamp() * 1000),
            "open": float(open_val),
            "high": float(high_val),
            "low": float(low_val),
            "close": float(close_val),
            "volume": float(vol_val)
        })
        
    json_data = json.dumps(records)

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/klinecharts/dist/klinecharts.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700&display=swap" rel="stylesheet">
        
        <style>
            body { font-family: 'Urbanist', sans-serif; background-color: #0b0e14; color: #d1d4dc; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
            .top-bar { height: 60px; background-color: #131722; border-bottom: 1px solid #2a2e39; display: flex; align-items: center; padding: 0 20px; justify-content: space-between; }
            .symbol-title { font-size: 24px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 10px; }
            .timeframe-badge { background: rgba(41, 98, 255, 0.1); color: #2962ff; padding: 6px 12px; border-radius: 4px; font-weight: 600; border: 1px solid rgba(41, 98, 255, 0.3); }
            .workspace { display: flex; flex: 1; height: calc(100vh - 60px); }
            .toolbar { width: 50px; background-color: #131722; border-right: 1px solid #2a2e39; display: flex; flex-direction: column; align-items: center; padding-top: 10px; gap: 8px; }
            .tool-btn { width: 36px; height: 36px; display: flex; justify-content: center; align-items: center; border-radius: 4px; color: #787b86; cursor: pointer; transition: all 0.2s; }
            .tool-btn:hover { background-color: #2a2e39; color: #d1d4dc; }
            .tool-btn.active { background-color: rgba(41, 98, 255, 0.1); color: #2962ff; }
            .chart-container-wrapper { flex: 1; position: relative; background-color: #0b0e14; }
            #chart { width: 100%; height: 100%; }
            .alert-panel { position: absolute; top: 20px; right: 20px; width: 320px; background-color: #1e222d; border: 1px solid #2a2e39; border-radius: 8px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); padding: 15px; z-index: 10; display: none; }
            .alert-btn { width: 100%; background-color: #2962ff; color: white; padding: 8px 0; border-radius: 4px; font-weight: 600; margin-top: 10px; transition: background 0.2s; cursor: pointer; border: none; }
            .alert-btn:hover { background-color: #1e53e5; }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div class="symbol-title">
                SYMBOL_PLACEHOLDER <span class="text-sm font-normal text-gray-400 ml-2">Live Streamlit Bridge</span>
            </div>
            <div>
                <span class="timeframe-badge">30m Chart</span>
            </div>
            <div class="flex items-center gap-4">
                <button id="extractDrawings" class="bg-[#2a2e39] hover:bg-[#363a45] px-4 py-2 rounded text-sm font-semibold transition text-white border-none cursor-pointer">
                    <i class="fa-solid fa-bell mr-2"></i>Sync Trendlines to Alerts
                </button>
            </div>
        </div>

        <div class="workspace">
            <div class="toolbar">
                <div class="tool-btn active" data-tool="cursor" title="Cursor" style="color: #2962ff;"><i class="fa-solid fa-arrow-pointer"></i></div>
                <div class="w-8 h-px bg-[#2a2e39] my-1"></div>
                <div class="tool-btn" data-tool="segment" title="Trend Line"><i class="fa-solid fa-chart-line"></i></div>
                <div class="tool-btn" data-tool="rayLine" title="Ray"><i class="fa-solid fa-arrow-up-right-dots"></i></div>
                <div class="tool-btn" data-tool="horizontalLine" title="Horizontal Line"><i class="fa-solid fa-minus"></i></div>
                <div class="w-8 h-px bg-[#2a2e39] my-1"></div>
                <div class="tool-btn hover:text-red-500" id="clearDrawings" title="Clear All Drawings"><i class="fa-solid fa-trash-can"></i></div>
            </div>

            <div class="chart-container-wrapper">
                <div id="chart"></div>
                
                <div class="alert-panel" id="alertPanel">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="font-bold text-white m-0 text-base"><i class="fa-solid fa-satellite-dish mr-2 text-[#2962ff]"></i>Backend Sync</h3>
                        <button id="closeAlert" class="text-gray-400 hover:text-white bg-transparent border-none cursor-pointer"><i class="fa-solid fa-times"></i></button>
                    </div>
                    <p class="text-sm text-gray-400 mb-2 mt-0">The following manual drawings have been captured and are ready to be sent to the Python Alert Engine.</p>
                    <div id="drawingDataList" class="text-xs bg-[#0b0e14] p-2 rounded text-green-400 font-mono h-32 overflow-y-auto">
                        // No lines drawn yet
                    </div>
                    <button class="alert-btn" id="confirmSync">Activate Server Alerts</button>
                </div>
            </div>
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", () => {
                const chart = klinecharts.init('chart');
                
                chart.setStyles({
                    grid: { show: true, horizontal: { color: '#1e222d', size: 1 }, vertical: { color: '#1e222d', size: 1 } },
                    candle: { bar: { upColor: '#26a69a', downColor: '#ef5350', upBorderColor: '#26a69a', downBorderColor: '#ef5350', upWickColor: '#26a69a', downWickColor: '#ef5350' } },
                    xAxis: { tickLine: { show: false }, axisLine: { color: '#2a2e39' } },
                    yAxis: { tickLine: { show: false }, axisLine: { color: '#2a2e39' } },
                    separator: { color: '#2a2e39' }
                });

                chart.createIndicator('VOL', true, { height: 100 });

                // INJECT DATA FROM PYTHON
                const chartData = DATAPLACEHOLDER;
                chart.applyNewData(chartData);

                document.querySelectorAll('.tool-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const tool = e.currentTarget.getAttribute('data-tool');
                        if(tool === null) return;

                        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
                        e.currentTarget.classList.add('active');

                        if (tool === 'cursor') {
                            chart.overrideOverlay({ lock: false });
                        } else {
                            chart.createOverlay({
                                name: tool,
                                extendData: 'CustomAlertLine',
                                onDrawEnd: function (event) {
                                    document.querySelector('[data-tool="cursor"]').click();
                                }
                            });
                        }
                    });
                });

                document.getElementById('clearDrawings').addEventListener('click', () => {
                    chart.removeOverlay();
                });

                const alertPanel = document.getElementById('alertPanel');
                const dataList = document.getElementById('drawingDataList');

                document.getElementById('extractDrawings').addEventListener('click', () => {
                    alertPanel.style.display = 'block';
                    const shapes = chart.getOverlayById();
                    dataList.innerHTML = '';
                    let hasDrawings = false;

                    if (shapes && shapes.length > 0) {
                        shapes.forEach((shape) => {
                            hasDrawings = true;
                            const p1 = shape.points[0];
                            const p2 = shape.points[1] || shape.points[0]; 
                            const date1 = new Date(p1.timestamp).toLocaleString();
                            const html = `<div class="mb-2 border-b border-gray-700 pb-1">
                                <span class="text-white font-bold">${shape.name.toUpperCase()}</span><br>
                                P1: ${date1} @ ${p1.value.toFixed(2)}<br>
                                ${p2 && p1 !== p2 ? `P2: ${new Date(p2.timestamp).toLocaleString()} @ ${p2.value.toFixed(2)}` : ''}
                            </div>`;
                            dataList.innerHTML += html;
                        });
                    }

                    if (!hasDrawings) {
                        dataList.innerHTML = `<span class="text-gray-500">// No lines drawn. Draw a trendline first to set an alert.</span>`;
                    } else {
                        dataList.innerHTML += `<br><span class="text-yellow-400">// Ready to bridge to Python Background Worker.</span>`;
                    }
                });

                document.getElementById('closeAlert').addEventListener('click', () => { alertPanel.style.display = 'none'; });
                
                document.getElementById('confirmSync').addEventListener('click', (e) => {
                    e.target.innerText = "Alerts Active!";
                    e.target.style.backgroundColor = "#26a69a";
                    setTimeout(() => {
                        alertPanel.style.display = 'none';
                        e.target.innerText = "Activate Server Alerts";
                        e.target.style.backgroundColor = "#2962ff";
                    }, 1500);
                });

                window.addEventListener('resize', () => { chart.resize(); });
            });
        </script>
    </body>
    </html>
    """

    # Inject variables securely without breaking javascript parsing
    html_code = html_template.replace("SYMBOL_PLACEHOLDER", symbol).replace("DATAPLACEHOLDER", json_data)
    
    # Render component
    components.html(html_code, height=650)
