#!/usr/bin/env python3
"""
eldo_plotter.py - High-Performance Multi-Pane Oscilloscope for SPICE Waveform Analysis.

Renders a dynamic pyqtgraph window with vertically stacked plot panes, linked X-axes,
and a global top-anchored crosshair cursor showing exact time and signal readouts.
"""

import sys
import os
import json
import argparse
import numpy as np
from PyLTSpice import RawRead
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

# Set pyqtgraph options for dark mode high performance rendering
pg.setConfigOption('background', '#18181b')  # Dark zinc theme
pg.setConfigOption('foreground', '#e4e4e7')
pg.setConfigOptions(antialias=True)

# Color palette for signal traces (high contrast neon/pastel colors)
SIGNAL_COLORS = [
    '#00ffff',  # Cyan
    '#ff007f',  # Pink / Magenta
    '#00ff66',  # Lime Green
    '#ffaa00',  # Amber / Orange
    '#a855f7',  # Purple
    '#38bdf8',  # Sky Blue
    '#facc15',  # Yellow
    '#ff4d4d',  # Red
]

def format_si_unit(val: float, unit: str = '') -> str:
    """Format floating point numbers into SI prefixed string (e.g. 1.234 ns, 500.00 mV)."""
    if abs(val) < 1e-18:
        return f"0.00 {unit}".strip()
    
    prefixes = [
        (1e9, 'G'), (1e6, 'M'), (1e3, 'k'), (1, ''),
        (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n'), (1e-12, 'p'), (1e-15, 'f')
    ]
    
    for scale, prefix in prefixes:
        if abs(val) >= scale * 0.999:
            scaled = val / scale
            return f"{scaled:.3f} {prefix}{unit}".strip()
            
    return f"{val:.3e} {unit}".strip()

def load_spice_data(filepath: str):
    """Parses binary or ASCII SPICE3 .raw or .spi3 simulation output file using PyLTSpice/spicelib."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: '{filepath}'")
        
    dialects = ['ltspice', 'ngspice', 'spice3', 'nutspice', None]
    raw = None
    last_err = None
    for d in dialects:
        try:
            raw = RawRead(filepath, dialect=d)
            break
        except Exception as e:
            last_err = e
            continue
            
    if raw is None:
        raise ValueError(f"Failed to parse SPICE output file '{filepath}': {last_err}")
        
    time_axis = raw.get_axis()
    trace_names = raw.get_trace_names()
    
    return raw, time_axis, trace_names

def find_trace_name(trace_names: list[str], target_signal: str) -> str | None:
    """Case-insensitive search for signal in SPICE trace list."""
    if target_signal in trace_names:
        return target_signal
    
    target_lower = target_signal.lower().strip()
    for t in trace_names:
        if t.lower().strip() == target_lower:
            return t
            
    for t in trace_names:
        if t.lower().replace('"', '').strip() == target_lower.replace('"', ''):
            return t
            
    return None

def create_default_layout(trace_names: list[str]) -> list[dict]:
    """Generates default layout if no layout is supplied (grouping voltages vs currents)."""
    voltages = [t for t in trace_names if t.lower() != 'time' and not t.lower().startswith('i')]
    currents = [t for t in trace_names if t.lower().startswith('i')]
    
    layout = []
    if voltages:
        layout.append({"pane_title": "Voltages", "signals": voltages})
    if currents:
        layout.append({"pane_title": "Currents", "signals": currents})
    if not layout:
        other = [t for t in trace_names if t.lower() != 'time']
        layout.append({"pane_title": "Waveforms", "signals": other})
    return layout

class WaveformVisualizer(QtWidgets.QMainWindow):
    def __init__(self, filepath: str, layout_config: list[dict]):
        super().__init__()
        self.filepath = filepath
        self.layout_config = layout_config
        
        # Read raw SPICE data directly into numpy arrays
        self.raw, self.time_axis, self.trace_names = load_spice_data(filepath)
        
        if not self.layout_config:
            self.layout_config = create_default_layout(self.trace_names)
            
        self.init_ui()
        
    def init_ui(self):
        filename = os.path.basename(self.filepath)
        self.setWindowTitle(f"EDA Waveform Visualizer - {filename}")
        self.resize(1100, 750)
        
        # Central Widget & Layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 10)
        main_layout.setSpacing(6)
        
        # Global Header / Synced Crosshair Status Readout anchored at top
        self.crosshair_label = QtWidgets.QLabel(f"File: {filename} | Hover over plots for synced crosshair readout")
        self.crosshair_label.setStyleSheet("""
            QLabel {
                background-color: #27272a;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 12px;
                border: 1px solid #3f3f46;
                border-radius: 6px;
            }
        """)
        self.crosshair_label.setWordWrap(True)
        main_layout.addWidget(self.crosshair_label)
        
        # GraphicsLayoutWidget for vertical stacked oscilloscope panes
        self.win = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.win)
        
        self.plot_panes = []
        self.crosshairs = []
        self.plotted_signals = {}  # pane_idx -> list of (signal_name, unit, wave_array, color_hex, label_item)
        
        first_pane = None
        color_idx = 0
        
        for pane_idx, pane_item in enumerate(self.layout_config):
            title = pane_item.get("pane_title", f"Pane {pane_idx + 1}")
            signals = pane_item.get("signals", [])
            
            if pane_idx > 0:
                self.win.nextRow()
                
            plot_item = self.win.addPlot(title=f"<span style='color: #ffffff; font-size: 12px; font-weight: bold;'>{title}</span>")
            plot_item.showGrid(x=True, y=True, alpha=0.3)
            plot_item.getAxis('bottom').setLabel('Time', color='#a1a1aa')
            plot_item.getAxis('left').setLabel('Magnitude', color='#a1a1aa')
            
            legend = plot_item.addLegend(offset=(10, 10), labelTextColor='#e4e4e7')
            legend.setBrush(pg.mkBrush(39, 39, 42, 200))
            legend.setPen(pg.mkPen(63, 63, 70, 255))
            
            # Synchronized X-Axes locking across all panes
            if first_pane is None:
                first_pane = plot_item
            else:
                plot_item.setXLink(first_pane)
                
            # Vertical InfiniteLine cursor for synchronized crosshair
            v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#ff3366', width=1.5, style=QtCore.Qt.PenStyle.DashLine))
            plot_item.addItem(v_line, ignoreBounds=True)
            self.crosshairs.append(v_line)
            
            self.plotted_signals[pane_idx] = []
            
            # Render signals overlaying each other in this pane
            for sig in signals:
                real_trace = find_trace_name(self.trace_names, sig)
                if real_trace is None:
                    print(f"Warning: Signal '{sig}' not found in SPICE output file.")
                    continue
                    
                wave = self.raw.get_trace(real_trace).get_wave()
                
                # Unit detection
                unit = 'V'
                if real_trace.lower().startswith('i') or '(i)' in real_trace.lower():
                    unit = 'A'
                    
                color = SIGNAL_COLORS[color_idx % len(SIGNAL_COLORS)]
                color_idx += 1
                
                pen = pg.mkPen(color=color, width=2)
                plot_item.plot(self.time_axis, wave, pen=pen, name=sig)
                
                label_item = legend.items[-1][1] if legend.items else None
                self.plotted_signals[pane_idx].append((sig, unit, wave, color, label_item))
                
            self.plot_panes.append(plot_item)
            
        # Connect mouse move event across all plots for synced crosshair and dynamic legend updates
        self.win.scene().sigMouseMoved.connect(self.on_mouse_moved)
        
    def on_mouse_moved(self, pos):
        if not self.plot_panes or len(self.time_axis) == 0:
            return
            
        mouse_point = None
        for pane in self.plot_panes:
            scene_rect = pane.sceneBoundingRect()
            if scene_rect.contains(pos):
                mouse_point = pane.vb.mapSceneToView(pos)
                break
                
        if mouse_point is None:
            mouse_point = self.plot_panes[0].vb.mapSceneToView(pos)
            
        x_val = mouse_point.x()
        
        # Check range bounds
        t_min, t_max = self.time_axis[0], self.time_axis[-1]
        if x_val < min(t_min, t_max) or x_val > max(t_min, t_max):
            return
            
        # Move synced crosshairs
        for v_line in self.crosshairs:
            v_line.setPos(x_val)
            
        # Locate exact time index
        idx = np.searchsorted(self.time_axis, x_val)
        idx = int(np.clip(idx, 0, len(self.time_axis) - 1))
        
        actual_time = self.time_axis[idx]
        formatted_time = format_si_unit(actual_time, 's')
        
        filename = os.path.basename(self.filepath)
        self.crosshair_label.setText(f"File: {filename}  |  Time: {formatted_time}")
        
        # Update dynamic legend in each plot pane with live signal values
        for pane_idx, sig_list in self.plotted_signals.items():
            for sig_name, unit, wave, color, label_item in sig_list:
                val = wave[idx]
                val_str = format_si_unit(val, unit)
                
                # Dynamic Legend Update: Update legend item text with live value
                if label_item is not None:
                    label_item.setText(f"<span style='color: {color}; font-weight: bold;'>{sig_name}: {val_str}</span>")

def main():
    parser = argparse.ArgumentParser(description="Multi-Pane Oscilloscope Waveform Visualizer for SPICE analysis.")
    parser.add_argument("--input", "-i", required=True, help="Path to standard SPICE3 .raw or .spi3 file")
    parser.add_argument("--layout", "-l", required=False, default="", help="JSON layout string defining plot panes and signals")
    
    args = parser.parse_args()
    
    layout_config = []
    if args.layout:
        try:
            layout_config = json.loads(args.layout)
        except json.JSONDecodeError as e:
            print(f"Error parsing layout JSON: {e}", file=sys.stderr)
            sys.exit(1)
            
    app = QtWidgets.QApplication(sys.argv)
    viewer = WaveformVisualizer(args.input, layout_config)
    viewer.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
