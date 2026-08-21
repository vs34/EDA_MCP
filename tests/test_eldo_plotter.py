import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from eldo_plotter import (
    load_spice_data,
    find_trace_name,
    format_si_unit,
    create_default_layout,
    WaveformVisualizer
)
from server import visualize_waveforms
from pyqtgraph.Qt import QtWidgets

class TestEldoPlotter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QtWidgets.QApplication.instance() is None:
            cls.app = QtWidgets.QApplication(sys.argv)
        else:
            cls.app = QtWidgets.QApplication.instance()
            
        cls.raw_path = os.path.join(base_dir, "workboard", "aoi32_sim", "aoi32_formats.raw")
        cls.spi3_path = os.path.join(base_dir, "workboard", "aoi32_sim", "aoi32_formats.spi3")

    def test_format_si_unit(self):
        self.assertEqual(format_si_unit(0.0, 'V'), '0.00 V')
        self.assertEqual(format_si_unit(1.2e-9, 's'), '1.200 ns')
        self.assertEqual(format_si_unit(500e-3, 'V'), '500.000 mV')
        self.assertEqual(format_si_unit(1.2, 'V'), '1.200 V')
        self.assertEqual(format_si_unit(2.5e3, 'Hz'), '2.500 kHz')

    def test_load_spice_data_raw(self):
        raw, time_axis, trace_names = load_spice_data(self.raw_path)
        self.assertGreater(len(time_axis), 0)
        self.assertIn('V(Y)', trace_names)
        self.assertIn('V(A1)', trace_names)

    def test_load_spice_data_spi3(self):
        raw, time_axis, trace_names = load_spice_data(self.spi3_path)
        self.assertGreater(len(time_axis), 0)
        self.assertIn('V(Y)', trace_names)
        self.assertIn('V(A1)', trace_names)

    def test_find_trace_name(self):
        traces = ['time', 'V(Y)', 'V(A1)', 'I(VDD)']
        self.assertEqual(find_trace_name(traces, 'v(y)'), 'V(Y)')
        self.assertEqual(find_trace_name(traces, 'V(A1)'), 'V(A1)')
        self.assertEqual(find_trace_name(traces, 'i(vdd)'), 'I(VDD)')
        self.assertIsNone(find_trace_name(traces, 'V(NONEXISTENT)'))

    def test_create_default_layout(self):
        traces = ['time', 'V(Y)', 'V(A1)', 'I(VDD)']
        layout = create_default_layout(traces)
        self.assertEqual(len(layout), 2)
        self.assertEqual(layout[0]['pane_title'], 'Voltages')
        self.assertEqual(layout[1]['pane_title'], 'Currents')

    def test_waveform_visualizer_panes(self):
        layout = [
            {"pane_title": "Output", "signals": ["V(Y)"]},
            {"pane_title": "Input", "signals": ["V(A1)"]}
        ]
        viewer = WaveformVisualizer(self.raw_path, layout)
        self.assertEqual(len(viewer.plot_panes), 2)
        self.assertIn(0, viewer.plotted_signals)
        self.assertEqual(viewer.plotted_signals[0][0][0], "V(Y)")

    def test_visualize_waveforms_tool_validation(self):
        # Missing file_path
        res = visualize_waveforms(file_path="", layout=[{"pane_title": "P", "signals": ["V(Y)"]}])
        self.assertTrue(res.startswith("Error:"))

        # Non-raw/spi3 extension
        res = visualize_waveforms(file_path="sim.txt", layout=[{"pane_title": "P", "signals": ["V(Y)"]}])
        self.assertTrue("must strictly target a .raw or .spi3" in res)

        # File does not exist
        res = visualize_waveforms(file_path="nonexistent.raw", layout=[{"pane_title": "P", "signals": ["V(Y)"]}])
        self.assertTrue("not found" in res)

        # Invalid layout
        res = visualize_waveforms(file_path=self.raw_path, layout=[])
        self.assertTrue("non-empty list" in res)

    @patch("subprocess.Popen")
    def test_visualize_waveforms_tool_success(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        layout = [
            {"pane_title": "Stimulus", "signals": ["V(A1)"]},
            {"pane_title": "Output", "signals": ["V(Y)"]}
        ]
        res = visualize_waveforms(file_path=self.raw_path, layout=layout)
        self.assertIn("Successfully launched PyQtGraph waveform visualizer", res)
        self.assertIn("PID: 12345", res)
        mock_popen.assert_called_once()

if __name__ == "__main__":
    unittest.main()
