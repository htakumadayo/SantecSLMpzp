import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from pzp_hardware.generic.mixins import image_preview
import numpy as np
import SantecSLM.interface as interface


""" Puzzlepiece pieces designed for Santec SLM(especially 200)"""

dummy_SLM_dimension = (1200, 1920)  # (height, width)


# Dict key of Puzzle.globals for SLM api object.
SANTEC_SLM_API = "SANTEC_SLM_API"

class SLMPiece(image_preview.ImagePreview, pzp.Piece):
    live_toggle = False # include a toggle to enable live mode
    autolevel_toggle = False # include a toggle to enable autoleveling
    max_counts = 1023 # the maximum image brightness (will be white with autolevel off)
    use_numba = False # if you need increased perfo
    horizontal_layout = True

    # String constants to access piece parameters and actions
    PARAM_DISPLAY_NB = "SLM Display number"
    PARAM_CTRL_NB = "SLM number"
    PARAM_WAVELENGTH = "Wavelength (nm)"
    PARAM_PHASE = "Phase"   # Maybe put an explicit description for this param
    PARAM_SLM_DIMENSIONS = "SLM dimensions"
    PARAM_WL_SAVE = "Save permanently λ and phase on update"

    ACTION_UPDATE_WL = "Update target wavelength and phase"

    def define_params(self):
        super().define_params()
        
        pzp.param.spinbox(self, SLMPiece.PARAM_DISPLAY_NB, 2, 1, 10, visible=False)(None)
        pzp.param.spinbox(self, SLMPiece.PARAM_CTRL_NB, 1, 1, 8, visible=False)(None)
        pzp.param.spinbox(self, SLMPiece.PARAM_WAVELENGTH, 635, 400, 1400, visible=False)(None)
        pzp.param.spinbox(self, SLMPiece.PARAM_PHASE, 200, 0, 999, visible=False)(None)
        pzp.param.checkbox(self, SLMPiece.PARAM_WL_SAVE, 1, visible=False)(None)

        pzp.param.array(self, SLMPiece.PARAM_SLM_DIMENSIONS, visible=False)(None)

        @pzp.param.connect(self)
        def connect():
            if self.puzzle.debug:
                self[SLMPiece.PARAM_SLM_DIMENSIONS].set_value(np.array(dummy_SLM_dimension))
                return 1
            
            # If not in debug mode
            slm = self.puzzle.globals[SANTEC_SLM_API]
            display_nb = self[SLMPiece.PARAM_DISPLAY_NB].value
            slm_nb = self[SLMPiece.PARAM_CTRL_NB].value

            disp_status = slm.SLM_Disp_Open(display_nb)
            ctrl_status = slm.SLM_Ctrl_Open(slm_nb)
            print(disp_status, ctrl_status)
            _, width, height = slm.SLM_Disp_Info(display_nb)
            _, wavelength, phase = slm.SLM_Ctrl_ReadWL(slm_nb)

            if disp_status == interface.SLM_OK and ctrl_status == interface.SLM_OK:
                self[SLMPiece.PARAM_SLM_DIMENSIONS].set_value(np.array((height, width)))
                self[SLMPiece.PARAM_WAVELENGTH].set_value(wavelength)
                self[SLMPiece.PARAM_PHASE].set_value(phase)
                return 1
            else:
                return 0

        @pzp.param.disconnect(self)
        def disconnect():
            if not self.puzzle.debug:
                slm = self.puzzle.globals[SANTEC_SLM_API]
                slm.SLM_Disp_Close(self[SLMPiece.PARAM_DISPLAY_NB].value)
                slm.SLM_Ctrl_Close(self[SLMPiece.PARAM_CTRL_NB].value)
            return 0
        
        @pzp.param.array(self, "image")
        def image():
            return self["image"].value
        
        @image.set_setter(self)
        def image_setter(value):
            if self["connected"].value is not True:
                return None
            slm_dim = self[SLMPiece.PARAM_SLM_DIMENSIONS].value.astype(int)
            if slm_dim[0] != value.shape[0] or slm_dim[1] != value.shape[1]:
                print(slm_dim, value.shape)
                raise ValueError("Image doesn't have same dimension as SLM")
            if not self.puzzle.debug:
                self.puzzle.globals[SANTEC_SLM_API].SLM_Disp_Data(
                    self[SLMPiece.PARAM_DISPLAY_NB].value,
                    value.shape[1], value.shape[0],
                    interface.FLAGS_COLOR_GRAY, value)
            return value
    
    def define_actions(self):
        @pzp.action.define(self, SLMPiece.ACTION_UPDATE_WL, visible=False)
        def updateslm(self):
            if self.puzzle.debug:
                print("Update")
                return
            if self["connected"].value is not True:
                return
            wl = self[SLMPiece.PARAM_WAVELENGTH].value
            phase = self[SLMPiece.PARAM_PHASE].value
            slm_nb = self[SLMPiece.PARAM_CTRL_NB].value
            slm = self.puzzle.globals[SANTEC_SLM_API]
            status = slm.SLM_Ctrl_WriteWL(slm_nb, wl, phase)
            if status != interface.SLM_OK:
                raise RuntimeError("SLM Error: Write WL failed")
            
            if self[SLMPiece.PARAM_WL_SAVE].value:
                status = slm.SLM_Ctrl_WriteAW(slm_nb)
                if status != interface.SLM_OK:
                    raise RuntimeError("SLM Error: Write AW failed")
                
        pzp.action.settings(self)

    def setup(self):
        if not self.puzzle.globals.require(SANTEC_SLM_API):
            # If there are multiple dlls, the user should specify only the directory and not all the dlls
            dll_path = "dll/x64/SLMFunc.dll"  # default
            dll_path = pht.config("santec_api_dll_path", 
                                  default=dll_path, 
                                  description="Santec SLM api dll", 
                                  validator=pht.validator_path_exists)
            self.puzzle.globals[SANTEC_SLM_API] = interface.SLM(dll_path)

if __name__ == "__main__":
    pass

