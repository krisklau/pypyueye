# -*- coding: utf-8 -*-
#!/usr/env python3

# Copyright (C) 2017 Gaby Launay

# Author: Gaby Launay  <gaby.launay@tutanota.com>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Gaby Launay"
__copyright__ = "Gaby Launay 2017"
__credits__ = ""
__license__ = "GPL3"
__version__ = ""
__email__ = "gaby.launay@tutanota.com"
__status__ = "Development"

import numpy as np
from pyueye import ueye
from threading import Thread
from .utils import ImageData, ImageBuffer, do_bin
import imageio as iio
import time
import spectral.io.envi as envi
from datetime import datetime

#Globals
#how often to flush the data stored in the envi file format to disk
ENVI_FLUSHING_N = 100


class GatherThread(Thread):
    def __init__(self, cam, copy=True):
        """
        Thread used for gather images.
        """
        super().__init__()
        self.timeout = 1000
        self.cam = cam
        self.cam.capture_video()
        self.running = True
        self.copy = copy
        self.d = 0
        self.capt_time = -1

    def run(self):
        while self.running:
            img_buffer = ImageBuffer()
            ret = ueye.is_WaitForNextImage(self.cam.handle(),
                                           self.timeout,
                                           img_buffer.mem_ptr,
                                           img_buffer.mem_id)
            if ret == ueye.IS_SUCCESS:
                self.capt_time = np.floor(time.time())*1000 + datetime.now().microsecond
                imdata = ImageData(self.cam.handle(), img_buffer)
                self._process(imdata)
            else:
                print("Warning: Missed %dth frame !"% self.d)
                self.d += 1

    def process(self, image_data):
        pass

    def _process(self, image_data):
        self.process(image_data)
        self.d += 1
        image_data.unlock()

    def stop(self):
        self.cam.stop_video()
        self.running = False


class FrameThread(GatherThread):
    def __init__(self, cam, views=None, copy=True):
        """
        Thread used for live display.
        """
        super().__init__(cam=cam, copy=copy)
        self.views = views

    def process(self, image_data):
        if self.views:
            if type(self.views) is not list:
                self.views = [self.views]
            for view in self.views:
                view.handle(image_data)


class UselessThread(GatherThread):
    def __init__(self, cam, views=None, copy=True):
        """
        Thread used for debugging only.
        """
        super().__init__(cam=cam, copy=copy)
        self.views = views

    def process(self, image_data):
        import numpy as np
        new_exp = np.random.rand()*20
        self.cam.set_exposure(new_exp)


class SaveThread(GatherThread):
    def __init__(self, cam, path, copy=True):
        """
        Thread used for saving one image.
        """
        super().__init__(cam=cam, copy=copy)
        self.path = path

    def process(self, image_data):
        iio.imwrite(self.path, image_data.as_1d_image())
        self.stop()

class MultiFrameThread(GatherThread):
    def __init__(self, cam, folder, base_name, max_frames=-1, file_type='.png', copy=True,
                 aoi=(), binning=(), do_print=False):
        """
        Thread used for saving multiple images.

        aoi is only needed for envi saving
        """

        print("starting")
        self.base_name = base_name
        if folder[-1] != '/':
            folder += '/'
        self.folder = folder
        self.file_type = file_type

        if aoi:
            self.aoi = aoi

        self.max_frames = max_frames
        if binning:
            self.binning = binning

        self.set_process()
        if do_print:
            self.print_2_process()
        print("process set")



        super().__init__(cam=cam, copy=copy)


    def time_str(self):
        return '{:.0f}'.format(self.capt_time) # in ms


    def set_path(self):
        self.path = self.folder + self.base_name + self.time_str() + '.' + self.file_type
        return self.path


    def stop_check(self):
        if self.max_frames > 0:
            if self.d + 2 > self.max_frames:
                self.stop()
                return True
            else:
                return False

    def set_data(self):
        if binning:
            def data(self, image_data):
                # bin along axis 0
                a = do_bin(image_data.as_1d_image(),
                           factor=self.binning[0],
                           axis=0)
                # bin along axis 1
                b = do_bin(a,
                           factor=self.binning[1],
                           axis=1)
                return b
        else:
            def data(self, image_data):
                return image_data.as_1d_image()

    def path(self):
        time_str = '{:.0f}'.format(self.capt_time*1000) # in ms
        return self.folder + self.base_name + str(int(self.capt_time)) + self.file_type

    def set_process(self):
        if self.file_type=='envi':
            # envi cannot rely on the iio lib
            self.prep_envi_capture()

            def process(self, image_data):
                #save data
                self.map[:, self.d, :] = image_data.as_1d_image()[:, :]
                if self.d % ENVI_FLUSHING_N == 0:
                    self.map.flush()
                #save timing
                with open(self.timings, 'a+') as ftimings:
                    ftimings.write(self.time_str() + ",")

                #end if max frames
                if self.stop_check():
                    self.map.flush()
        elif self.file_type=='.bip':
            def process(self, image_data):
                image_data.as_1d_image().astype(np.int16).tofile(self.path())
                print(self.path())
                self.stop_check()
        else:
            def process(self, image_data):
                iio.imwrite(self.path(), image_data.as_1d_image())
                self.stop_check()

        self.process = lambda image_data: process(self, image_data)

    def print_2_process(self):
        def _process(self, image_data):
            self.process(image_data)
            self.d += 1
            print(self.d)
            image_data.unlock()
        self._process = lambda image_data: _process(self, image_data)


    def prep_envi_capture(self):
        # define the metadata
        md = {
                 "bands": self.aoi[3],
                 "lines": self.aoi[2],
                 "samples": self.max_frames,
                 "data type": 12,
                 "interleave": 'bip'
             }
        # determine saving location
        self.loc = self.folder + self.base_name + ".hdr"
        print(self.loc)
        self.timings = self.folder + self.base_name + "_timings.csv"

        #initialize datacube and timings
        self.envi = envi.create_image(self.loc, md)
        self.map = self.envi.open_memmap(writable=True)

        return self.map, self.timings

class old_MultiFrameThread(GatherThread):
    def __init__(self, cam, folder, base_name, max_frames=-1, file_type='.png', copy=True):
        """
        Thread used for saving multiple images.
        """
        super().__init__(cam=cam, copy=copy)

        self.base_name = base_name
        if folder[-1] != '/':
            folder += '/'
        self.folder = folder
        self.file_type = file_type

        self.max_frames = max_frames

    def path(self):
        time_str = '{:.0f}'.format(self.capt_time*1000) # in ms
        return self.folder + self.base_name + str(int(self.capt_time)) + self.file_type

    def process(self, image_data):
        iio.imwrite(self.path(), image_data.as_1d_image())

        if self.max_frames > 0:
            if self.d + 2 > self.max_frames:
                self.stop()

