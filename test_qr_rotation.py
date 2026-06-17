import cv2
import numpy as np

def simulate(W, H, old_x, old_y, rotation):
    # simulate rotating an image of size WxH
    # old_x, old_y are coordinates in the unrotated image
    if rotation == 0:
        return old_x, old_y
    elif rotation == 90: # CW
        new_W, new_H = H, W
        new_x = new_W - old_y
        new_y = old_x
        return new_x, new_y
    elif rotation == 180:
        new_W, new_H = W, H
        new_x = new_W - old_x
        new_y = new_H - old_y
        return new_x, new_y
    elif rotation == 270: # CCW
        new_W, new_H = H, W
        new_x = old_y
        new_y = new_H - old_x
        return new_x, new_y

W, H = 800, 500
old_x, old_y = 700, 100 # Top Right

print("Original W, H =", W, H)
for rot in [0, 90, 180, 270]:
    nx, ny = simulate(W, H, old_x, old_y, rot)
    nW, nH = (H, W) if rot in [90, 270] else (W, H)
    quadrant = ""
    if nx > nW/2 and ny < nH/2: quadrant = "Top-Right"
    elif nx > nW/2 and ny > nH/2: quadrant = "Bottom-Right"
    elif nx < nW/2 and ny < nH/2: quadrant = "Top-Left"
    elif nx < nW/2 and ny > nH/2: quadrant = "Bottom-Left"
    
    print(f"Rot {rot}: pos=({nx},{ny}) center=({nW/2},{nH/2}) -> {quadrant}")
