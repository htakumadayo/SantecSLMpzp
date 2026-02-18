import time
import numpy as np
import puzzlepiece as pzp


# Utility class to fetch image and intensity from camera
class CameraImageFetcher:
    def __init__(self, puzzle: pzp.Puzzle, wait_time: float=0):
        self.puzzle = puzzle
        self.wait_time = wait_time

    def get_image_from_camera(self):
        time.sleep(self.wait_time)
        self.puzzle.process_events()
        # time.sleep(0.05)
        # self.puzzle.process_events()
        return self.puzzle["Camera"]["image"].value.astype(np.int16)
    
    # Should be useless as Camera piece can do it
    def set_backbround(self):
        self.background = self.get_image_from_camera()
        print(self.background.dtype)
    
    def get_processed_image(self):
        if not hasattr(self, "background"):
            self.background = 0
        return np.maximum(0, self.get_image_from_camera() - self.background)
    #

    def get_intensity(self):
        intensity = np.sum(self.get_processed_image())
        return intensity
    

def get_sorted_peak_idx(image, axis=1, threshold=100):
    arr = np.sum(image, axis=axis)
    local_max = (np.diff(arr, append=arr[-1]) < 0) & (np.diff(arr, prepend=arr[0]) > 0) & (arr > threshold)

    peak_idx = np.nonzero(local_max)[0]
    sorted_peaks_idx = np.argsort(arr[peak_idx])[::-1]

    return peak_idx[sorted_peaks_idx]
    
# n: order of polynomial
def fit(x, y, n):
    n += 1
    power = np.arange(n)
    X = np.tile(x, (n, 1)).T ** power
    P = np.linalg.inv(X.T @ X)
    parameters = P @ X.T @ y

    N, p = X.shape
    delta_sq = np.sum( (y - X @ parameters)**2 ) / (N-p)
    return parameters, np.diag(delta_sq * P)

def simulate_fit(x, params):
    n = params.size
    return np.tile(x, (n, 1)).T ** np.arange(0,n) @ params

def save_csv(x, y, name):
    data = np.vstack((x, y)).T
    np.savetxt(name, data)