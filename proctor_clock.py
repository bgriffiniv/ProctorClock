#!/usr/bin/env python
# coding: UTF-8
# license: GPL
#
## @package _08c_clock
#
#  A very simple analog Clock.
#
#  The program transforms worldcoordinates into screencoordinates
#  and vice versa according to an algorithm found in:
#  "Programming principles in computer graphics" by Leendert Ammeraal.
#
#  Based on the code of Anton Vredegoor(anton.vredegoor@gmail.com)
#
#  @author Paulo Roma
#  @since 01/05/2014
#  @see https://code.activestate.com/recipes/578875-analog-Clock
#  @see http://orion.lcg.ufrj.br/python/figuras/fluminense.png

import sys, os
from datetime import timedelta, datetime
from math import sin, cos, pi
from threading import Thread
try:
    from tkinter import Tk, Canvas, BOTH, YES, ALL       # python 3
except ImportError:
    try:
        from mtTkinter import Tk, Canvas, BOTH, YES, ALL  # for thread safe
    except ImportError:
        try:
            from Tkinter import Tk, Canvas, BOTH, YES, ALL    # python 2
        except ImportError:
            print("Cannot find Tkinter")

HAS_PIL = True
# we need PIL for resizing the background image
# in Fedora do: yum install python-pillow-tk
# or yum install python3-pillow-tk
try:
    from PIL import Image, ImageTk
except ImportError:
    HAS_PIL = False



## Class for handling the mapping from window coordinates
#  to viewport coordinates.
#
class Mapper:
    ## Constructor.
    #
    #  @param world window rectangle.
    #  @param viewport screen rectangle.
    #
    def __init__(self, world, viewport):
        self.world = world
        self.viewport = viewport
        # default initial world size is a 2-by-2 grid with min-max points at
        # [-1(x-min), -1(y-min), 1(x-max), 1(y-max)]
        # other initial grid anchor points are possible with their own effects
        # Remember that, from the screen's perspective, y increases downward
        # whereas, from the world's perspective, y increases upward!

        # window coordinates
        x_min_world, y_min_world, x_max_world, y_max_world = self.world
        # screen coordinates
        x_min_viewport, y_min_viewport, x_max_viewport, y_max_viewport = self.viewport
        # window factor
        x_factor = float(x_max_viewport-x_min_viewport) / float(x_max_world-x_min_world)
        y_factor = float(y_max_viewport-y_min_viewport) / float(y_max_world-y_min_world)
        self.factor = min(x_factor, y_factor) # From the x and y fractions pick the smallest
        # Center point of the world
        x_center_world = 0.5 *(x_min_world + x_max_world)
        y_center_world = 0.5 *(y_min_world + y_max_world)
        # Center point of the viewport (window in screen coordinates)
        x_center_viewport = 0.5 *(x_min_viewport + x_max_viewport)
        y_center_viewport = 0.5 *(y_min_viewport + y_max_viewport)
        # Center offsets
        self.c_1 = x_center_viewport - self.factor * x_center_world
        self.c_2 = y_center_viewport - self.factor * y_center_world
        #print(world)
        #print(viewport)
        #print(self.factor)
        #print(self.c_1)
        #print(self.c_2)

    ## Maps a single point from world(window) coordinates to viewport(screen) coordinates.
    #
    #  @param x, y given point.
    #  @return a new point in screen coordinates.
    #
    def _window_to_viewport(self, x_world, y_world):
        x_viewport = self.factor *  x_world + self.c_1
        y_viewport = self.factor * -y_world + self.c_2      # y_viewport axis is upside down
        return x_viewport, y_viewport

    ## Maps two points from world(window) coordinates to viewport(screen) coordinates.
    #
    #  @param x1, y1 first point.
    #  @param x2, y2 second point.
    #  @return two new points in screen coordinates.
    #
    def window_to_viewport(self, x_world_1, y_world_1, x_world_2, y_world_2):
        world_point_1 = self._window_to_viewport(x_world_1, y_world_1)
        world_point_2 = self._window_to_viewport(x_world_2, y_world_2)
        return world_point_1, world_point_2



## Class for creating a new thread.
#
class MakeThread(Thread):
    """Creates a thread."""

    ## Constructor
    #  @param func function to run on this thread.
    #
    def __init__(self, func):
        Thread.__init__(self)
        self.__action = func
        self.debug = False

    ## Destructor
    #
    def __del__(self):
        if self.debug:
            print("Thread end")

    ## Starts this thread(called by self.start())
    #
    def run(self):
        if self.debug:
            print("Thread begin")
        self.__action()



## Class for drawing a simple analog Clock.
#  The backgroung image may be changed by pressing key 'i'.
#  The image path is hardcoded. It should be available in directory 'images'.
#
class Clock:
    ## Constructor.
    #
    #  @param root the Tkinder GUI API
    #  @param delta_hours time zone.
    #  @param is_show_image whether to use a background image.
    #  @param width canvas width.
    #  @param height canvas height.
    #  @param is_use_thread whether to use a separate thread for running the Clock.
    #
    def __init__(self, root, delta_hours=0, is_show_image=True, width=400, height=400, is_use_thread=False):
        self.world = [-1, -1, 1, 1]
        self.img_path = './images/fluminense.png'  # image path
        if HAS_PIL and os.path.exists(self.img_path): # no(in Windows) and no(path doesn't exist)
            self.show_image = is_show_image
        else:
            self.show_image = False # this is probably what we'll get most times

        self.set_colors() # sets colors based on show_image value
        self.circlesize = 0.09 # defines the radius of the center circle as 0.09 ??
        self._all = 'handles' # no idea what this does yet
        self.root = root
        width, height = width, height
        self.pad = width/16 # not sure why we're basing the padding on the width but okay
        self.d_minutes = 0
        self.d_hours = 0
        flu = None
        self.flu = None

        if self.show_image: # nope
            self.flu_img = Image.open(self.img_path)

        self.root.bind("<Escape>", lambda _: root.destroy()) # more tkinter stuff
        self.delta = timedelta(hours=delta_hours)
        self.canvas = Canvas(root, width=width, height=height, background=self.bgcolor)
        viewport = (self.pad, self.pad, width-self.pad, height-self.pad) # create viewport with
                                                                         # padded values

        self.my_mapper = Mapper(self.world, viewport) # create Mapper for the window that will be created
        self.root.title('Clock')
        self.root.bind("<Configure>", self.resize)
        self.root.bind("<KeyPress-i>", self.toggle_image)
        self.root.bind("<KeyPress-f>", self.add_minute) # forward one minute
        self.root.bind("<KeyPress-v>", self.subtract_minute) # reverse one minute
        self.root.bind("<space>", self.reset_time) # reset minutes
        self.root.bind("<KeyPress-F>", self.add_hour) # forward one hour
        self.root.bind("<KeyPress-V>", self.subtract_hour) # reverse one hour
        self.canvas.pack(fill=BOTH, expand=YES) # ???

        if is_use_thread:
            new_thread = MakeThread(self.poll)
            new_thread.debug = True
            new_thread.start()
        else:
            self.poll()

    ## Called when the window changes, by means of a user input.
    #
    def resize(self, event):
        if event:
            my_canvas = self.canvas
            my_canvas.delete(ALL)            # erase the whole canvas
            width = my_canvas.winfo_width() # get new window width
            height = my_canvas.winfo_height() # get new window height

            img_size = min(width, height)
            self.pad = img_size/16 # AHA! padding does scale up with min(width, height)
            viewport = (self.pad, self.pad, width-self.pad, height-self.pad)
            self.my_mapper = Mapper(self.world, viewport)

            if self.show_image: # nope
                flu = self.flu_img.resize((int(0.8*0.8*img_size), int(0.8*img_size)), Image.ANTIALIAS)
                if flu:
                    self.flu = ImageTk.PhotoImage(flu)
                    my_canvas.create_image(width/2, height/2, image=self.flu)
            else:
                self.canvas.create_rectangle([[0, 0], [width, height]], fill=self.bgcolor)
                # Why are we calling create_rectangle(...) all of a sudden?
            self.redraw()             # redraw the Clock

    ## Sets the Clock colors.
    #
    def set_colors(self):
        if self.show_image: # nope
            self.bgcolor = 'antique white'
            self.timecolor = 'dark orange'
            self.circlecolor = 'dark green'
            self.secondcolor = 'red'
        else:
            self.bgcolor = '#000000'
            self.timecolor = '#ffffff'
            self.circlecolor = '#e0e0e0' # originally, #808080
            self.secondcolor = '#ff0000'

    ## Toggles the displaying of a background image.
    #
    def toggle_image(self, event):
        if HAS_PIL and os.path.exists(self.img_path): # nope
            self.show_image = not self.show_image
            self.set_colors()
            self.resize(event)

    ## Redraws the whole Clock.
    #
    def redraw(self):
        start = pi/2              # 12h is at pi/2 ~ 90*
        step = pi/6               # each step is pi/6 ~ 30*
        for i in range(12):       # draw the minute ticks as circles
            angle = start-i*step
            x_coord, y_coord = cos(angle), sin(angle)
            self.paint_circle(x_coord, y_coord) # draw number(i) at(x, y)
        self.paint_hms()           # draw the handles
        if not self.show_image:
            self.paint_circle(0, 0)  # draw a circle at the centre of the Clock

    ## Set Clock forward or back by a given number of minutes
    #
    def seek_time(self, hour_change=0, minute_change=0):
        self.d_minutes += minute_change
        self.d_hours += hour_change
        self.redraw()

    def add_minute(self, event):
        if event:
            self.seek_time(minute_change=1)

    def subtract_minute(self, event):
        if event:
            self.seek_time(minute_change=-1)

    def add_hour(self, event):
        if event:
            self.seek_time(hour_change=1)

    def subtract_hour(self, event):
        if event:
            self.seek_time(hour_change=-1)

    def reset_time(self, event):
        if event:
            #self.seek_time(hour_change=-1*self.d_hours, minute_change=-1*self.d_minutes)
            self.d_hours = 0
            self.d_minutes = 0
            self.redraw()

    ## Draws the handles.
    #
    def paint_hms(self):
        self.canvas.delete(self._all)  # delete the handles
        current_datetime = datetime.timetuple(datetime.utcnow()-self.delta)
        trash, trash, trash, hour, minute, second, trash, trash, trash = current_datetime
        if trash:
            trash = None
        minute = (minute + self.d_minutes) % 60
        hour = (hour + self.d_hours) % 12
        self.root.title('%02i:%02i:%02i' %(hour, minute, second))
        angle = pi/2 - pi/6 *(hour + minute/60.0)
        x_coord, y_coord = cos(angle)*0.60, sin(angle)*0.60
        scl = self.canvas.create_line
        # draw the hour handle
        scl(self.my_mapper.window_to_viewport(0, 0, x_coord, y_coord), fill=self.timecolor, tag=self._all,
            width=self.pad/3)

        angle = pi/2 - pi/30 *(minute + second/60.0)
        x_coord, y_coord = cos(angle)*0.90, sin(angle)*0.90
        # draw the minute handle
        scl(self.my_mapper.window_to_viewport(0, 0, x_coord, y_coord), fill=self.timecolor, tag=self._all,
            width=self.pad/5)

        angle = pi/2 - pi/30 * second
        x_coord, y_coord = cos(angle)*0.95, sin(angle)*0.95
        # draw the second handle
        scl(self.my_mapper.window_to_viewport(0, 0, x_coord, y_coord), fill=self.secondcolor, tag=self._all,
            width=self.pad/15)

    ## Draws a circle at a given point.
    #
    #  @param x, y given point.
    #
    def paint_circle(self, x_coord, y_coord):
        circle_size = self.circlesize / 2.0
        sco = self.canvas.create_oval
        sco(self.my_mapper.window_to_viewport(-circle_size+x_coord, -circle_size+y_coord, circle_size+x_coord, circle_size+y_coord),
            fill=self.circlecolor)

    ## Animates the Clock, by redrawing everything after a certain time interval.
    #
    def poll(self):
        self.redraw()
        self.root.after(200, self.poll)



## Main program for testing.
#
#  @param argv time zone, image background flag,
#         Clock width, Clock height, create thread flag.
#
def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) > 2:
        try:
            delta_hours = int(argv[1])
            is_show_image = (argv[2] == 'True')
            width = int(argv[3])
            height = int(argv[4])
            is_use_thread = (argv[5] == 'True')
        except ValueError:
            print("A timezone is expected.")
            return 1
    else:
        delta_hours = 5 # EST
        is_show_image = True
        width = height = 400
        is_use_thread = False

    root = Tk() # TODO: find out what this and the following does
    root.geometry('+0+0')
    # delta_hours: how far are you from utc?
    # Sometimes the Clock may be run from another timezone ...
    Clock(root, delta_hours, is_show_image, width, height, is_use_thread)
    root.mainloop() # This officially starts the window and binds its event listeners

    # Create a new window
    # With space for the new time







if __name__ == '__main__':
    sys.exit(main())
