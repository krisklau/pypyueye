#!/bin/python3
import argparse

from pyueye import ueye
from pypyueye import Camera as Cam
from pypyueye.threads import MultiFrameThread

# Setting up argparse
parser = argparse.ArgumentParser('capture images')
parser.add_argument('captured_images_path', metavar='path',
                    type=str, help='folder where data will be stored',
                    default='~/tmp')
parser.add_argument('base_name', metavar='base', default='TEST', type=str,
                    help='base name for the saved files')
parser.add_argument('-f', '--fps',
                    default=20, help='frames per second to be captured' )
parser.add_argument('-n', '--number_of_frames',
                    default=100, help='total number of frames to capture' )
parser.add_argument('-t', '--file_type', default="jpg",
                    help='frames or images will be stored as this filetype')

args = parser.parse_args()

# assigning the arguments to variables for simple backwards compatibility
FPS = args.fps
FOLDER = args.captured_images_path
BASE_NAME = args.base_name
MAX_FRAMES = args.number_of_frames
FILE_TYPE = '.' + args.file_type


# DEFAULTS
AOI = (0,0,1088,2048)
PIXEL_CLOCK = 160

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

    thread = MultiFrameThread(c, folder=FOLDER, base_name=BASE_NAME,
                              max_frames=MAX_FRAMES, file_type=FILE_TYPE,
                              aoi=AOI)
    thread.start()
    thread.join()
