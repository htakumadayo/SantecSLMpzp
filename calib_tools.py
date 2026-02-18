import puzzlepiece as pzp
import os
import time
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from SantecSLM.pzp import SLMPiece
import SantecSLM.patterns as pat
# from pzp_hardware.oceanoptics import spectrometer
import SantecSLM.utility as util
import pandas as pd
from pyqtgraph.Qt import QtWidgets
from puzzlepiece.extras import hardware_tools as pht
import pyqtgraph as pg


class OceanSpectrometer(pzp.Piece):
    """
    A very basic Piece for getting values and wavelengths from an OceanOptics
    spectrometer. Contributions welcome to expose more options!

    .. image:: ../images/pzp_hardware.oceanoptics.spectrometer.Piece.png
    """
    custom_horizontal = True

    def define_params(self):
        @pzp.param.dropdown(self, "spectrometer", "")
        def list_spectrometers():
            if not self.puzzle.debug:
                return self.imports.list_devices()

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                return 1
            self.spec = self.imports.Spectrometer.from_serial_number(
                self.params['spectrometer'].get_value().split(":")[1][:-1]
            )

        @pzp.param.disconnect(self)
        def disconnect():
            if self.puzzle.debug:
                return 0
            if self._ensure(capture_exception=True):
                self.spec.close()
            return 0

        pzp.param.array(self, 'wls', False)(None)
        pzp.param.array(self, 'background_spec', False)(None)
        pzp.param.checkbox(self, 'Subtract background', True, True)(None)

        @pzp.param.array(self, 'values')
        @self._ensure
        def values():
            if self.puzzle.debug:
                wls, vals = np.arange(100), np.random.random(100)
                self.params['wls'].set_value(wls)
                return vals
            
            wls, vals = self.spec.spectrum()
            if self['Subtract background'].value and self['background_spec'].value is not None:
                vals = np.maximum(0, vals - self['background_spec'].value)
            self.params['wls'].set_value(wls)
            return vals
        
        @pzp.param.spinbox(self, "Integration time (μs)", 10000)
        @self._ensure
        def exposure(value):
            if self.puzzle.debug:
                return value
            self.spec.integration_time_micros(value)

    def define_actions(self):
        @pzp.action.define(self, "Set background")
        def set_background():
            self["background_spec"].set_value(self["values"].value)
            print("Background set.")

    @pzp.piece.ensurer
    def _ensure(self):
        if not self.puzzle.debug and not hasattr(self, 'spec'):
            raise("Spectrometer not connected")

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()

        # The thread runs self.get_value repeatedly, which updates the plot through the
        # Signal connection defined below
        self.timer = pzp.threads.PuzzleTimer('Live', self.puzzle, self.params['values'].get_value, 0.05)
        layout.addWidget(self.timer)

        self.pw = pg.PlotWidget()
        layout.addWidget(self.pw)
        self.plot = self.pw.getPlotItem()
        self.plot_line = self.plot.plot([0], [0], symbol='o', symbolSize=3)

        # Update the plot when the values change (through a CallLater, so the
        # update is done only when the GUI loop is running)
        def update_plot():
            self.plot_line.setData(
                self.params['wls'].value,
                self.params['values'].value
            )
        update_later = pzp.threads.CallLater(update_plot)
        self.params['values'].changed.connect(update_later)

        return layout

    def setup(self):
        pht.requirements(
            {
                "seabreeze": {
                    "pip": "seabreeze",
                    "url": "https://python-seabreeze.readthedocs.io/en/latest/install.html"
                }
            }
        )
        import seabreeze.spectrometers
        self.imports = seabreeze.spectrometers
    

# Calibration 2: Uniform pattern, Grayscale calibration

# TOdo? maybe also check what happens if we add offset to grating
# Calibration 3: Binary grating efficiency.
class UniformAndBinaryCalib(pzp.Piece):
    """
    Piece that measures wavelength wise calibration data of the SLM. 2 modes are available; Grayscale calibration mode and Binary grating efficiency mode. 
    Uses OceanOptics spectrometer to fetch data.
    
    Uniform pattern mode should be used with a 45deg polarizer (with respect to SLM operating axis) before and after SLM.

    Binary grating mode works only with a lens (at focal distance).
    
    :var Assumptions: Description
    :var arrays: Description
    """
    PARAM_MODE = "Calibration mode"
    PARAM_SAMPLE_NB = "Sample number"
    PARAM_CAPT_INTERVAL = "Sampling interval (ms)"
    PARAM_MAX_WL = "Max wavelength (nm)"
    PARAM_MIN_WL = "Min wavelength (nm)"
    PARAM_NORMALIZE = "Normalize over"
    PARAM_FILENAME = "Save file name"
    PARAM_CALIB_DATA = "Calibration data"
    PARAM_CALIB_WL = "Calibration wl"

    PARAM_SPEC_NAME = "Spectrometer piece name"
    PARAM_UNIFORM_NAME = "Uniform pattern piece name"
    PARAM_BINARY_NAME = "Binary grating pattern piece name"

    MODE_EFF = "BinaryEfficiency"
    MODE_GRAY = "GrayscaleCalibration"

    NORM_NONE = "None"
    NORM_ALL = "All"
    NORM_PER_WL = "Per wavelength"

    ACTION_MEASURE = "Measure"

    def define_params(self):
        pzp.param.dropdown(self, self.PARAM_MODE, self.MODE_EFF)([self.MODE_EFF, self.MODE_GRAY])
        pzp.param.spinbox(self, self.PARAM_SAMPLE_NB, 30, 1, 9999)(None)
        pzp.param.spinbox(self, self.PARAM_CAPT_INTERVAL, 50.0, 0.05, 9999, v_step=5.0)(None)
        pzp.param.spinbox(self, self.PARAM_MAX_WL, 1550, 1, 99999)(None)
        pzp.param.spinbox(self, self.PARAM_MIN_WL, 1050, 1, 99999)(None)
        pzp.param.dropdown(self, self.PARAM_NORMALIZE, self.NORM_NONE)([self.NORM_NONE, self.NORM_ALL, self.NORM_PER_WL])
        pzp.param.text(self, self.PARAM_FILENAME, f"calib{self.MODE_EFF}.csv")(None)
        pzp.param.array(self, self.PARAM_CALIB_DATA, False)(None)
        pzp.param.array(self, self.PARAM_CALIB_WL, False)(None)

        pzp.param.text(self, self.PARAM_SPEC_NAME, OceanSpectrometer.__name__, visible=False)(None)
        pzp.param.text(self, self.PARAM_UNIFORM_NAME, pat.UniformPattern.__name__, visible=False)(None)
        pzp.param.text(self, self.PARAM_BINARY_NAME, pat.BinaryGratingPattern.__name__, visible=False)(None)
        pzp.action.settings(self)

    def define_actions(self):
        @pzp.action.define(self, self.ACTION_MEASURE)
        def measure():
            sample_nb = self[self.PARAM_SAMPLE_NB].value
            min_wl, max_wl = self[self.PARAM_MIN_WL].value, self[self.PARAM_MAX_WL].value
            wait_time = self[self.PARAM_CAPT_INTERVAL].value / 1000
            grating: pat.BinaryGratingPattern = self.puzzle[self[self.PARAM_BINARY_NAME].value]
            uniform: pat.UniformPattern = self.puzzle[self[self.PARAM_UNIFORM_NAME].value]
            spec: OceanSpectrometer = self.puzzle[self[self.PARAM_SPEC_NAME].value]
            save_name = self[self.PARAM_FILENAME].value

            spec_wavelengths = spec["wls"].value
            spec_mask = (min_wl <= spec_wavelengths) & (spec_wavelengths <= max_wl)

            mode = self[self.PARAM_MODE].value
            contrasts = np.linspace(0, 1023, sample_nb).astype(int)
            spectrums = [None] * sample_nb

            if mode == self.MODE_EFF:
                grating[pat.BinaryGratingPattern.PARAM_DUTY_CYCLE].set_value(0.5)

            target_piece = grating if self.MODE_EFF else uniform
            target_piece[target_piece.PARAM_PHASE].set_value(0)
            target_piece.actions[target_piece.ACTION_SEND]()
            time.sleep(1)
            self.puzzle.process_events()

            for i, contrast in enumerate(contrasts):
                target_piece[target_piece.PARAM_PHASE].set_value(contrast)
                target_piece.actions[target_piece.ACTION_SEND]()
                time.sleep(wait_time)
                self.puzzle.process_events()
                spectrums[i] = spec["values"].value[spec_mask]

            spectrums = np.array(spectrums)

            nm_per_wl = False
            nm_all = False
            if self[self.PARAM_NORMALIZE].value == self.NORM_PER_WL:
                nm_per_wl = True
                spectrums /= np.max(spectrums, axis=0)
            elif self[self.PARAM_NORMALIZE].value == self.NORM_ALL:
                nm_all = True
                spectrums /= np.max(spectrums)
            effective_wls = spec_wavelengths[spec_mask]

            self[self.PARAM_CALIB_DATA].set_value(spectrums)
            self[self.PARAM_CALIB_WL].set_value(effective_wls)

            plt.imshow(spectrums, origin="lower", aspect="auto", extent=[np.min(effective_wls), np.max(effective_wls), 0, 1023])
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Phase (Grayscale)")
            cbar = plt.colorbar()
            cbar.set_label(f"{"Relative" if nm_all or nm_per_wl else ""} Intensity {"per wavelength" if nm_per_wl else ""}")
            plt.savefig(f"{save_name}.svg")
            plt.show()

            df = pd.DataFrame(spectrums, index=contrasts, columns=effective_wls)
            df.to_csv(f"{save_name}.csv")

# receives row by row calibration data
# linear interpolation 
# 1. find the usable part of the curve (Pick next point at the same height and same slope)
# The samples between the beginning and that point is one period of cos^2. 
# If no such point is found, then take all
# 
# 2. Apply inverse cos^2. Let the obtained value φ'.
# 3. If the slope at a given point is positive, then transform φ'-> pi-φ'
# 4. Subtract pi from everything before 0, so that we get a continuous map
# 5. Then subtract from all the absolute value of first value
# 6. Multiply everything by 2
def map_grayscale_to_phase(grayscales, intensities, ignored_samples=1):
    """
    Computes the map between grayscales and phases using results from the 45deg polarizer experiment.
    2 Assumptions:
    - Intensity is monotonically increasing until it reaches maximum. In other words, maximum comes before minimum.
    - No irregular points, i.e. fluctuations that make the slope non "Continuous". i.e. if the curve is globally 
        increasing, there shouldn't be points that make the curve locally decreasing.

    Return a tuple of two arrays: (grayscales, phases)

    :param grayscales: Grayscale values of the samples
    :param intensities:  Measured intensities corresponding to the grayscales
    :param ignored_samples: Ignored sample number to the right and the left of global minimum to avoid experimental imperfections. Mainly due to residual intensities.
    """
    x, y = grayscales, intensities
    if np.max(y) > 1:
        y /= np.max(y)

    slopes = np.sign(np.diff(y, append=y[-1]))
    dist_from_1st = np.sign(y - y[0])
    period_delim = np.sign(np.diff(dist_from_1st, append=dist_from_1st[-1])) == slopes[0]

    if period_delim.size > 1:
        period_end_idx = np.argmax(period_delim[1:])+1
        x = x[0:period_end_idx]
        y = y[0:period_end_idx]
        slopes = slopes[0:period_end_idx]

    ignore_mask = np.ones_like(x, dtype=bool)
    ignore_mask[np.argmin(y)-ignored_samples : np.argmin(y)+ignored_samples+1] = 0
    x,y,slopes = x[ignore_mask], y[ignore_mask], slopes[ignore_mask]

    phases = np.acos(np.sqrt(y))
    phases[slopes > 0] = np.pi - phases[slopes > 0]
    zero_idx = np.argmin(np.abs(phases - 0))
    phases[0:zero_idx] -= np.pi
    phases -= phases[0]
    phases *= 2
    if x[-1] != 1023:
        phases = np.append(phases, 2*np.pi)
        x = np.append(x, 1023)
    return x, phases


def linear_interpolation(target, x, y):
    """
    Given two arrays that (discretely) represent some function, apply that function to a given array 
    using linear interpolation.
    
    :param target: Array that you want to apply the function to.
    :param x: Arguments
    :param y: Images correspondting to the arguments
    """
    if np.min(target) < np.min(x) or np.max(target) > np.max(x):
        raise ValueError("Linear interpolation failed: Some target values not in range of x")

    # Find what coefficients to use
    diff = np.tile(x, (target.size, 1)).T - target
    interp_coef_idx = x.size - np.argmax(diff[::-1, :] <= 0, axis=0) - 1
    # Repeat last value to avoid indexing issues
    x = np.append(x, x[-1] + 1)  # Avoid divison by zero
    y = np.append(y, y[-1])
    
    # Interpolation formula
    slope = (y[interp_coef_idx + 1] - y[interp_coef_idx]) / (x[interp_coef_idx + 1] - x[interp_coef_idx])
    result = y[interp_coef_idx] + (target - x[interp_coef_idx])*slope
    return result


class PhaseCorrector(pat.PatternGenerator):
    """
    Piece that corrects binary grating pattern based on calibration data from UniformAndBinaryCalib
    """
    PARAM_MIN_WL = "Min. wavelength"
    PARAM_MAX_WL = "Max. wavelength"
    PARAM_IGNORE = "Ignored samples"
    PARAM_CORRECTION = "Correction data"
    PARAM_CALIB_PIECE_NAME = "Calibration piece name"

    def define_params(self):
        pzp.param.spinbox(self, self.PARAM_MIN_WL, 1050, 1, 9999999)(None)
        pzp.param.spinbox(self, self.PARAM_MAX_WL, 1400, 1, 9999999)(None)
        pzp.param.spinbox(self, self.PARAM_IGNORE, 1, 0, 9999)(None)
        # Column by column (per wavelength) correction data. Each index correcspond to a (2,N) shape matrix that contains calibration curve.
        pzp.param.array(self, self.PARAM_CORRECTION, False)(None) 
        pzp.param.text(self, self.PARAM_CALIB_PIECE_NAME, UniformAndBinaryCalib.__name__, visible=False)(None)
        super().define_params()

    def define_actions(self):
        @pzp.action.define(self, "Get correction data")
        def get_calib_data():
            measure_piece = self.puzzle[self[self.PARAM_CALIB_PIECE_NAME].value]
            measure_piece[UniformAndBinaryCalib.PARAM_MODE].set_value(UniformAndBinaryCalib.MODE_GRAY)
            measure_piece[UniformAndBinaryCalib.PARAM_NORMALIZE].set_value(UniformAndBinaryCalib.NORM_PER_WL)
            measure_piece.actions[UniformAndBinaryCalib.ACTION_MEASURE]()
            data = measure_piece[UniformAndBinaryCalib.PARAM_CALIB_DATA].value
            wls = measure_piece[UniformAndBinaryCalib.PARAM_CALIB_WL].value
            colbycol_calib = []
            col_nb = self.puzzle[self.get_slm_piece_name()][SLMPiece.PARAM_IMAGE].value.shape[1]
            max_wl, min_wl = self[self.PARAM_MAX_WL].value, self[self.PARAM_MIN_WL].value
            for col in range(col_nb):   # Are wavelengths scattered linearly?? -> Assume yes
                assumed_wl = min_wl + col*(max_wl - min_wl)/col_nb
                calib_idx = np.argmin(np.abs(wls - assumed_wl))
                calib = data[calib_idx, :]
                colbycol_calib.append(calib)
            self[self.PARAM_CORRECTION].set_value(np.stack(colbycol_calib))
        super().define_actions()

    def generate_pattern(self, slm_dim):
        pattern = self.puzzle[self.get_slm_piece_name()][SLMPiece.PARAM_IMAGE].value.T * 2*np.pi
        ignore = self[self.PARAM_IGNORE].value
        correction_data = self[self.PARAM_CORRECTION].value
        corrected_grayscales = []
        for row in range(pattern.shape[0]):  # I realized later that wavelengths are spread along axis 1 and not 0
            grayscale, phase = map_grayscale_to_phase(correction_data[row][0, :], correction_data[row][1,:], ignore)
            corrected_grayscale = linear_interpolation(pattern[row, :], phase, grayscale)
            corrected_grayscales.append(corrected_grayscale)
        corrected_pattern = np.stack(corrected_grayscales, dtype=int).T  # So fix it here
        return corrected_pattern
    


class Polarizer45degHelper(pzp.Piece):
    """
    Helper piece to align polariser at 45deg with respect to SLM operating axis
    """

    PARAM_UNIFORM = "Uniform pattern piece name"
    PARAM_INTERVAL = "Sampling interval (ms)"


    def define_params(self):
        pzp.param.spinbox(self, self.PARAM_INTERVAL, 50, 1, 5000, v_step=50)(None)
        pzp.param.text(self, self.PARAM_UNIFORM, pat.UniformPattern.__name__)(None)
        self.fetcher = util.CameraImageFetcher(self.puzzle)

    def define_actions(self):
        @pzp.action.define(self, "Set background image")
        def set_background():
            self.fetcher.set_backbround()

        @pzp.action.define(self, "Find max and min locations")
        def find_max_min():
            sample_nb = 40
            self.uniform_generator = self.puzzle[self[self.PARAM_UNIFORM].value]
            phases = np.linspace(0, 1023, sample_nb, dtype=int)
            intensities = np.zeros_like(phases)

            self.set_phase_and_get_intensity(0)
            time.sleep(1)

            for i, phase in enumerate(phases):
                intensity = self.set_phase_and_get_intensity(phase)
                intensities[i] = intensity
                self.puzzle.process_events()

            # Initial guess
            A0 = np.max(intensities) - np.min(intensities)
            E0 = np.min(intensities)
            C0 = np.pi/1023      # rough guess for frequency
            D0 = 0.0      # phase guess
            p0 = [A0, C0, D0, E0]

            # Fit
            cos2_model = lambda x,A,C,D,E: A*(np.cos(C*x+D)**2)+E
            popt, pcov = curve_fit(cos2_model, phases, intensities, p0=p0)

            # Find min and max locations
            C_fit = popt[1]
            D_fit = popt[2]

            test = np.linspace(0, 1023, 2000, dtype=int)
            test_image = cos2_model(test, *popt)
            min_x = test[np.argmin(test_image)]
            max_x = test[np.argmax(test_image)]
            self.min_max = (min_x, max_x)

            # Just a preview
            x_fit = np.linspace(0, 1023, 1000)
            y_fit = cos2_model(x_fit, *popt)
            plt.scatter(phases, intensities)
            plt.plot(x_fit, y_fit)
            plt.scatter((min_x, max_x), cos2_model(np.array((min_x,max_x)), *popt), c='r')
            plt.show()
        
        @pzp.action.define(self, "Measure contrast")
        def measure_contrast():
            if not hasattr(self, "min_max"):
                raise RuntimeError("Please first measure min and max locations")
            
            min_intensity = self.set_phase_and_get_intensity(self.min_max[0])
            max_intensity = self.set_phase_and_get_intensity(self.min_max[1])
            print(f"Minimum: {min_intensity:.1f}, Maximum: {max_intensity:.1f}, Extinction ratio: {min_intensity/max_intensity:.4f}")


    def set_phase_and_get_intensity(self, phase):
        interval = self[self.PARAM_INTERVAL].value
        self.uniform_generator[pat.UniformPattern.PARAM_PHASE].set_value(phase)
        self.uniform_generator.actions[pat.PatternGenerator.ACTION_SEND]()
        time.sleep(interval/1000)
        return self.fetcher.get_intensity()
    