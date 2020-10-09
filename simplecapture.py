#!/bin/python3
from pyueye import ueye
from pypyueye import Camera as Cam
from pypyueye.threads import MultiFrameThread

FPS = 5
AOI = (0,0,1088,2048)
PIXEL_CLOCK = 100
FOLDER = "~/tmp"
BASE_NAME = "test"
MAX_FRAMES = 10

with Cam() as c:
    c.set_colormode(ueye.IS_CM_MONO8)
    #c.set_aoi(0,0,c.,800)
    
    c.set_pixelclock(PIXEL_CLOCK)
    c.set_fps(FPS)
    actual_fps = c.get_fps()
    c.set_exposure(1/actual_fps*1000)
    c.set_aoi(*AOI)
    aoi = c.get_aoi()
    
    print(f"MODIFIED VALUES")
    print(f'fps: {c.get_fps()}')
    print(f'Available fps range: {c.get_fps_range()}')
    print(f'Pixelclock: {c.get_pixelclock()}')
    print(f'aoi: {aoi.height}, {aoi.width}')
    pixel_clock = c.get_pixelclock()
    exposure = c.get_exposure()
    
    print(f'handle: {c.handle()}')
        
    thread = MultiFrameThread(c, folder=FOLDER, base_name=BASE_NAME, max_frames=MAX_FRAMES)
    thread.start()
    thread.join()