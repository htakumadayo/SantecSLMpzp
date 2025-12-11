import ctypes
from ctypes import wintypes
import numpy as np

""" Santec SLM-200 interface for python. """

# Typedefs and Constants below
DWORD  = wintypes.DWORD           # unsigned 32-bit
USHORT = wintypes.WORD            # unsigned 16-bit
BYTE   = wintypes.BYTE            # unsigned 8-bit
INT32  = ctypes.c_int32           # signed 32-bit

HBITMAP = wintypes.HBITMAP        # handle to bitmap
LPSTR   = ctypes.c_char_p         # char* (ANSI)
LPCSTR  = ctypes.c_char_p         # const char*
LPCWSTR = ctypes.c_wchar_p        # const wchar_t*
LPDWORD = ctypes.POINTER(DWORD)
LPUSHORT = ctypes.POINTER(USHORT)

SLM_STATUS = ctypes.c_int         # typedef int SLM_STATUS;

FLAGS_COLOR_NOP   = 0x00000000
FLAGS_COLOR_R     = 0x00000001
FLAGS_COLOR_G     = 0x00000002
FLAGS_COLOR_B     = 0x00000004
FLAGS_COLOR_GRAY  = 0x00000008
FLAGS_COLOR_10BIT = 0x00000100
FLAGS_RATE120     = 0x20000000

SLM_OK = 0  # OK
SLM_NG = 1	# NG
SLM_BS = 2	# Busy
SLM_ER = 3  # parameter ER
SLM_INVAID_MONITOR = -1  # not find display no
SLM_NOT_OPEN_MONITOR = -2  # not open display
SLM_OPEN_WINDOW_ERR = -3  # window open error
SLM_DATA_FORMAT_ERR = -4  # data foramt error
SLM_FILE_READ_ERR = -101  # not find  file
SLM_NOT_OPEN_USB = -200  # not open usb
SLM_OTHER_ERROR = -1000  # other error
SLM_FTDI_ERROR  = -10000
# End of typedefs and constants 

class SLM:
    def __init__(self, path_to_dll=None):
        if path_to_dll is not None:
            self.init_slm(path_to_dll)

    def init_slm(self, path):
        self.slm = ctypes.CDLL(path)
        self._link_dll_to_python()

    def _link_dll_to_python(self):
        # Display functions
        self.slm.SLM_Disp_Open.argtypes = [DWORD]
        self.slm.SLM_Disp_Open.restype = SLM_STATUS

        self.slm.SLM_Disp_Info.argtypes = [DWORD, LPUSHORT, LPUSHORT]
        self.slm.SLM_Disp_Info.restype = SLM_STATUS

        self.slm.SLM_Disp_GrayScale.argtypes = [DWORD, DWORD, USHORT]
        self.slm.SLM_Disp_GrayScale.restype = SLM_STATUS

        self.slm.SLM_Disp_Close.argtypes = [DWORD]
        self.slm.SLM_Disp_Close.restype = SLM_STATUS

        self.slm.SLM_Disp_Data.argtypes = [DWORD, USHORT, USHORT, DWORD, LPUSHORT]
        self.slm.SLM_Disp_Data.restype = SLM_STATUS

        self.slm.SLM_Disp_ReadBMP.argtypes = [DWORD, DWORD, LPCWSTR]
        self.slm.SLM_Disp_ReadBMP.restype = SLM_STATUS

        self.slm.SLM_Disp_ReadCSV.argtypes = [DWORD, DWORD, LPCWSTR]
        self.slm.SLM_Disp_ReadCSV.restype = SLM_STATUS

        # Control functions
        self.slm.SLM_Ctrl_Open.argtypes = [DWORD]
        self.slm.SLM_Ctrl_Open.restype = SLM_STATUS

        self.slm.SLM_Ctrl_ReadSU.argtypes = [DWORD]
        self.slm.SLM_Ctrl_ReadSU.restype = SLM_STATUS

        self.slm.SLM_Ctrl_WriteVI.argtypes = [DWORD, DWORD]
        self.slm.SLM_Ctrl_WriteVI.restype = SLM_STATUS
        
        self.slm.SLM_Ctrl_ReadVI.argtypes = [DWORD, LPDWORD]
        self.slm.SLM_Ctrl_ReadVI.restype = SLM_STATUS

        self.slm.SLM_Ctrl_WriteWL.argtypes = [DWORD, DWORD, DWORD]
        self.slm.SLM_Ctrl_WriteWL.restype = SLM_STATUS

        self.slm.SLM_Ctrl_ReadWL.argtypes = [DWORD, LPDWORD, LPDWORD]
        self.slm.SLM_Ctrl_ReadWL.restype = SLM_STATUS

        self.slm.SLM_Ctrl_Close.argtypes = [DWORD]
        self.slm.SLM_Ctrl_Close.restype = SLM_STATUS

        self.slm.SLM_Ctrl_WriteAW.argtypes = [DWORD]
        self.slm.SLM_Ctrl_WriteAW.restype = SLM_STATUS

        

    def SLM_Disp_Open(self, DisplayNumber):
        """
        SLM display initializing.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Disp_Open(DWORD(DisplayNumber))
    
    def SLM_Disp_Info(self, DisplayNumber):
        """
        Read width and height of the display.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
        
        Returns:
            Tuple of three elements:
                0: SLM_OK if successful, otherwise SLM_STATUS error code is returned.
                1: Width of the display
                2: Height of the display
        """
        width = USHORT()
        height = USHORT()
        status = self.slm.SLM_Disp_Info(DWORD(DisplayNumber), ctypes.byref(width), ctypes.byref(height))
        return status, width.value, height.value
    
    def SLM_Disp_GrayScale(self, DisplayNumber, Flags, GrayScale):
        """
        Drawing the entire display with GrayScale input.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
            Flags (int): Use this to change the display method. 
            GrayScale (int): Specify grayscale from 0 to 1023 (0pi to 2pi).
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Disp_GrayScale(DWORD(DisplayNumber), DWORD(Flags), USHORT(GrayScale))

    def SLM_Disp_Close(self, DisplayNumber):
        """
        SLM display finalizing.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Disp_Close(DWORD(DisplayNumber))

    def SLM_Disp_Data(self, DisplayNumber, width, height, Flags, data):
        """
        Display array data on the SLM.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
            width (int): Specify display width value.
            height (int): Specify display height value.
            Flags (int): Use this to change the display method.
            data (np.array): Numpy array of positive ints (< 1024) with dimension (height, width)  
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        ptr = np.ascontiguousarray(data.flatten().astype(np.int16)).ctypes.data_as(LPUSHORT)
        return self.slm.SLM_Disp_Data(DWORD(DisplayNumber), USHORT(width), USHORT(height),
                                      DWORD(Flags), ptr)
    
    def SLM_Disp_ReadBMP(self, DisplayNumber, Flags, FileName):
        """
        Display array data on the SLM.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
            Flags (int): Use this to change the display method.
            FileName (str): Python string containing bmp file name.
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Disp_ReadBMP(DWORD(DisplayNumber), DWORD(Flags), FileName)

    def SLM_Disp_ReadCSV(self, DisplayNumber, Flags, FileName):
        """
        Display array data on the SLM.
        Args:
            DisplayNumber (int): Specify display number (1, 2, 3…).
            Flags (int): Use this to change the display method.
            FileName (str): Python string containing csv file name.
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Disp_ReadCSV(DWORD(DisplayNumber), DWORD(Flags), FileName)


    # Control functions
    def SLM_Ctrl_Open(self, SLMNumber):
        """
        Open USB interface.
        Args:
            SLMNumber (int): Specify SLM number (1-8).
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Ctrl_Open(DWORD(SLMNumber))
    
    def SLM_Ctrl_ReadSU(self, SLMNumber):
        """
        Read status of SLM. Busy or Ready.
        Args:
            SLMNumber (int): Specify SLM number (1-8).
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Ctrl_ReadSU(DWORD(SLMNumber))
    
    def SLM_Ctrl_WriteVI(self, SLMNumber, mode):
        """
        Write video mode DVI or Memory mode.
        Args:
            SLMNumber (int): Specify SLM number (1-8).
            mode (int): Specify mode value. 0:Memory mode, 1:DVI mode
        
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Ctrl_WriteVI(DWORD(SLMNumber), DWORD(mode))
    
    def SLM_Ctrl_ReadVI(self, SLMNumber):
        """
        Read display mode DVI or Memory mode.
        Args:
            SLMNumber (int): Specify SLM number (1-8).
        
        Returns:
            Tuple of two elements:
                0: SLM_OK if successful, otherwise SLM_STATUS error code is returned.
                1: Mode value: 0=Memory mode, 1=DVI mode
        """
        mode = DWORD()
        status = self.slm.SLM_Ctrl_ReadVI(DWORD(SLMNumber), ctypes.byref(mode))
        return status, mode.value
    
    def SLM_Ctrl_WriteWL(self, SLMNumber, wavelength, phase):
        """
        Write wavelength and phase value.
        It cannot be set to a value that causes internal calculation result of SLM to be abnormal.
        e.g. Set phase 2.00pi => calculation result 2.01pi
        Args:
            SLMNumber (int): Specify SLM number (1-8).
            wavelength (int): Specify wavelength value.(e.g. 1500)
            phase (int): Specify phase value multiplied by 100 (0-999). e.g. 2.00pi => 200. 
                Note: This phase is the maximum optical phase at specified wavelength, i.e. 1023 corresponds to the phase value given to this parameter.
        
        Returns:
                SLM_OK if successful, otherwise SLM_STATUS error code is returned.

        Note: The setting takes approx. 30 to 40 seconds
        """
        return self.slm.SLM_Ctrl_WriteWL(DWORD(SLMNumber), DWORD(wavelength), DWORD(phase))
    
    def SLM_Ctrl_ReadWL(self, SLMNumber):
        """
        Read wavelength and phase value.
        
        Args:
            SLMNumber (int): Specify SLM number (1-8).
            
        Returns:
            Tuple of two elements:
                0: SLM_OK if successful, otherwise SLM_STATUS error code is returned.
                1: Wavelength value: wavelength value. (450-1600)
                2: phase value multiplied by 100. (0-999)
        """
        wavelength = DWORD()
        phase = DWORD()
        status = self.slm.SLM_Ctrl_ReadWL(DWORD(SLMNumber), ctypes.byref(wavelength), ctypes.byref(phase))
        return status, wavelength.value, phase.value
    
    def SLM_Ctrl_WriteAW(self, SLMNumber):
        """
        Save wavelength and phase settings.
        The settings are retained even when power is turned off.
        
        Args:
            SLMNumber (int): Specify SLM number (1-8).
            
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Ctrl_WriteAW(DWORD(SLMNumber))
    
    def SLM_Ctrl_Close(self, SLMNumber):
        """
        Close USB interface.
        
        Args:
            SLMNumber (int): Specify SLM number (1-8).
            
        Returns:
            SLM_OK if successful, otherwise SLM_STATUS error code is returned.
        """
        return self.slm.SLM_Ctrl_Close(DWORD(SLMNumber))

if __name__ == "__main__":
    slm = SLM("dll/x64/SLMFunc.dll")
    status = slm.SLM_Disp_Open(2)
    slm.SLM_Disp_GrayScale(2, FLAGS_COLOR_10BIT, 512)
