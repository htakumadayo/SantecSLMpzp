from SantecSLM.pzp import SLMPiece
import puzzlepiece as pzp
import numpy as np


# in meters
pixel_pitch = 8*1e-6

class PatternGenerator():
    ACTION_SEND = "Send"

    def check_slm_status(self):
        """
        Method provided for pattern generators to check SLM availability.
        If the SLM is connected, return the dimension of slm, in the format (height, width)
        Otherwise return None.
        """
        slm = self.puzzle["SLM"]
        if slm["connected"].value is not True:
            return None
        slm_dim = slm[SLMPiece.PARAM_SLM_DIMENSIONS].value
        return slm_dim
    
    def send_image_to_slm(self, pattern):
        self.puzzle["SLM"]["image"].set_value(pattern)


class BasicBlazedGrating(pzp.Piece, PatternGenerator):
    def define_params(self):
        pzp.param.spinbox(self, "Period", 50, 2, 3000)(None)
        pzp.param.spinbox(self, "Max phase", 1023, 0, 1023)(None)

    def blazed_grating_x(self, height, width, period_px, max_phase):
        x = np.arange(width)
        k = x % period_px
        row = k * max_phase / (period_px - 1)  # shape (width,)
        grating = np.tile(row, (height, 1))  # shape (height, width)
        return grating

    def define_actions(self):
        @pzp.action.define(self, PatternGenerator.ACTION_SEND)
        def generate():
            slm_dim = self.check_slm_status()
            if slm_dim is None:
                return
            period = self["Period"].value
            max_phase = self["Max phase"].value
            self.send_image_to_slm(self.blazed_grating_x(slm_dim[0], slm_dim[1], period, max_phase))
    

class UniformPattern(pzp.Piece, PatternGenerator):
    PARAM_PHASE = "Phase"

    def define_params(self):
        pzp.param.spinbox(self, UniformPattern.PARAM_PHASE, 50, 2, 3000)(None)
    
    def define_actions(self):
        @pzp.action.define(self, PatternGenerator.ACTION_SEND)
        def generate():
            slm_dim = self.check_slm_status()
            if slm_dim is None:
                return
            phase = self[UniformPattern.PARAM_PHASE].value
            self.send_image_to_slm(np.ones(slm_dim)*phase)


def clamp(value, min_, max_):
    return min(max(value, min_), max_)

def mm_to_px(value):
    return round((value/1000)/pixel_pitch)

# 0 phase for slit opening and 512 (pi) phase for the 'wall'
class SlitPattern(pzp.Piece, PatternGenerator):
    def define_params(self):
        pzp.param.checkbox(self, "Vertical", 1)(None)
        pzp.param.spinbox(self, "Slit width (mm)", 1.0, 0.01, 16, v_step=0.1)(None)
        pzp.param.spinbox(self, "Offset (mm)", 0.0, -8, 8, v_step=0.1)(None)

        pzp.param.checkbox(self, "Double slits", 0)(None)
        pzp.param.spinbox(self, "Distance between center of two slits (mm)", 0.5, 0.01, 16, v_step=0.1)(None)

        pzp.param.spinbox(self, "Opening phase", 0, 0, 1023, visible=False)(None)
        pzp.param.spinbox(self, "Wall phase", 512, 0, 1023, visible=False)(None)

    def define_actions(self):
        pzp.action.settings(self)

        @pzp.action.define(self, PatternGenerator.ACTION_SEND)
        def generate():
            slm_dim = self.check_slm_status()
            if slm_dim is None:
                return
            vertical = self["Vertical"].value
            double = self["Double slits"].value
            width = self["Slit width (mm)"].value
            offset = self["Offset (mm)"].value
            opening_phase = self["Opening phase"].value
            wall_phase = self["Wall phase"].value


            def draw_slit(pattern_base, vertical, width, offset, slm_dim, phase):
                half_width_px = mm_to_px(width/2)
                offset_px = mm_to_px(offset)
                slm_length_px = (slm_dim[1] if vertical else slm_dim[0])
                center_idx = round(slm_length_px / 2) + offset_px

                start = clamp(center_idx - half_width_px, 0, slm_length_px) 
                end = clamp(center_idx + half_width_px, 0, slm_length_px)
                if vertical:
                    pattern_base[:, start:end] = phase
                else:
                    pattern_base[start:end, :] = phase


            pattern = np.ones(slm_dim)*wall_phase
            if double:
                interval = self["Distance between center of two slits (mm)"].value
                draw_slit(pattern, vertical, width, offset + interval/2, slm_dim, opening_phase)
                draw_slit(pattern, vertical, width, offset - interval/2, slm_dim, opening_phase)
            else:
                draw_slit(pattern, vertical, width, offset, slm_dim, opening_phase)
            self.send_image_to_slm(pattern)


class PinholePattern(pzp.Piece, PatternGenerator):
    def define_params(self):
        pzp.param.spinbox(self, "Slit radius (mm)", 0.5, 0.01, 8, v_step=0.1)(None)
        pzp.param.spinbox(self, "Offset X (mm)", 0.0, -8, 8, v_step=0.1)(None)
        pzp.param.spinbox(self, "Offset Y (mm)", 0.0, -8, 8, v_step=0.1)(None)

        pzp.param.spinbox(self, "Opening phase", 0, 0, 1023, visible=False)(None)
        pzp.param.spinbox(self, "Wall phase", 512, 0, 1023, visible=False)(None)

    def define_actions(self):
        @pzp.action.define(self, PatternGenerator.ACTION_SEND)
        def generate():
            slm_dim = self.check_slm_status()
            if slm_dim is None:
                return
            radius = self["Slit radius (mm)"].value
            offset_x = self["Offset X (mm)"].value
            offset_y = self["Offset Y (mm)"].value
            opening_phase = self["Opening phase"].value
            wall_phase = self["Wall phase"].value

            pattern = np.ones(slm_dim)*wall_phase
            yy, xx = np.mgrid[:slm_dim[0], :slm_dim[1]]
            mask = ((xx - mm_to_px(offset_x) - slm_dim[1]/2)**2 + (yy - mm_to_px(offset_y) - slm_dim[0]/2)**2) < mm_to_px(radius)**2
            pattern[mask] = opening_phase
            self.send_image_to_slm(pattern)
        pzp.action.settings(self)

