#!/usr/bin/env python
# coding: UTF-8
# license: GPL
#
## @package _08c_clock
#
#  A very simple analog clock.
#
#  The program transforms worldcoordinates into screencoordinates 
#  and vice versa according to an algorithm found in: 
#  "Programming principles in computer graphics" by Leendert Ammeraal.
#
#  Based on the code of Anton Vredegoor (anton.vredegoor@gmail.com) 
#
#  @author Paulo Roma
#  @since 01/05/2014
#  @see https://code.activestate.com/recipes/578875-analog-clock
#  @see http://orion.lcg.ufrj.br/python/figuras/fluminense.png

import sys, types, os
from time import localtime
from datetime import timedelta,datetime
from math import sin, cos, pi
from threading import Thread
try:
	from tkinter import *       # python 3
except ImportError:
	try:
	   from mtTkinter import *  # for thread safe
	except ImportError:
	   from Tkinter import *    # python 2

hasPIL = True
# we need PIL for resizing the background image
# in Fedora do: yum install python-pillow-tk
# or yum install python3-pillow-tk
try:
	from PIL import Image, ImageTk
except ImportError:
	hasPIL = False

## Class for handling the mapping from window coordinates
#  to viewport coordinates.
#
class mapper:
	## Constructor.
	#
	#  @param world window rectangle.
	#  @param viewport screen rectangle.
	#
	def __init__(self, world, viewport):
		self.world = world 
		self.viewport = viewport
		# default initial world size is a 2-by-2 grid with min-max points at
		# [-1 (x-min), -1 (y-min), 1 (x-max), 1 (y-max)]
		# other initial grid anchor points are possible with their own effects
		# Remember that, from the screen's perspective, y increases downward
		# whereas, from the world's perspective, y increases upward!
		x_min, y_min, x_max, y_max = self.world # window coordinates
		X_min, Y_min, X_max, Y_max = self.viewport # screen coordinates
		f_x = float(X_max-X_min) / float(x_max-x_min) # window factor (x-axis) 
		f_y = float(Y_max-Y_min) / float(y_max-y_min) # window factor (y-axis)
		self.f = min(f_x,f_y) # From the x and y fractions pick the smallest
		x_c = 0.5 * (x_min + x_max) # Halfway across the window (x-axis)
		y_c = 0.5 * (y_min + y_max) # Halfway down the window (y-axis)
		X_c = 0.5 * (X_min + X_max) # Halfway across the on-screen window (x-axis)
		Y_c = 0.5 * (Y_min + Y_max) # Halfway down the on-screen window (y-axis)
		self.c_1 = X_c - self.f * x_c # Center point of on-screen window (x-axis)
		self.c_2 = Y_c - self.f * y_c # Center point of on-screen window (y-axis)
		#print (world)
		#print (viewport)
		#print (self.f)
		#print (self.c_1)
		#print (self.c_2)

	## Maps a single point from world (window) coordinates to viewport (screen) coordinates.
	#
	#  @param x, y given point.
	#  @return a new point in screen coordinates.
	#
	def __windowToViewport(self, x, y):
		X = self.f *  x + self.c_1
		Y = self.f * -y + self.c_2      # Y axis is upside down 
		return X , Y

	## Maps two points from world (window) coordinates to viewport (screen) coordinates.
	#
	#  @param x1, y1 first point.
	#  @param x2, y2 second point.
	#  @return two new points in screen coordinates.
	#
	def windowToViewport(self,x1,y1,x2,y2):
		return self.__windowToViewport(x1,y1),self.__windowToViewport(x2,y2)

## Class for creating a new thread.
#
class makeThread (Thread):
	  """Creates a thread."""

	  ## Constructor
	  #  @param func function to run on this thread.
	  #
	  def __init__ (self,func):
		  Thread.__init__(self)
		  self.__action = func
		  self.debug = False

	  ## Destructor
	  #
	  def __del__ (self):
		  if ( self.debug ): print ("Thread end")

	  ## Starts this thread (called by self.start())
	  #
	  def run (self):
		  if ( self.debug ): print ("Thread begin")
		  self.__action()

## Class for drawing a simple analog clock.
#  The backgroung image may be changed by pressing key 'i'.
#  The image path is hardcoded. It should be available in directory 'images'.
#
class clock:
	## Constructor.
	#
	#  @param root the Tkinder GUI API
	#  @param deltahours time zone.
	#  @param sImage whether to use a background image.
	#  @param w canvas width.
	#  @param h canvas height.
	#  @param useThread whether to use a separate thread for running the clock.
	#
	def __init__(self,root,deltahours = 0,sImage = True,w = 400,h = 400,useThread = False):
		self.world       = [-1,-1,1,1]
		self.imgPath     = './images/fluminense.png'  # image path
		if hasPIL and os.path.exists (self.imgPath): # no (in Windows) and no (path doesn't exist)
		   self.showImage = sImage
		else:
		   self.showImage = False # this is probably what we'll get most times

		self.setColors() # sets colors based on showImage value
		self.circlesize = 0.09 # defines the radius of the center circle as 0.09 ??
		self._ALL       = 'handles' # no idea what this does yet
		self.root       = root
		width, height   = w, h
		self.pad        = width/16 # not sure why we're basing the padding on the width but okay
		self.dMinutes   = 0
		self.dHours     = 0

		if self.showImage: # nope
		   self.fluImg = Image.open(self.imgPath)

		self.root.bind("<Escape>", lambda _ : root.destroy()) # more tkinter stuff
		self.delta = timedelta(hours = deltahours)
		self.canvas = Canvas(root, width = width, height = height, background = self.bgcolor)
		viewport = (self.pad,self.pad,width-self.pad,height-self.pad) # create viewport with padded values
		self.T = mapper(self.world,viewport) # create mapper for the window that will be created
		self.root.title('Clock')
		self.root.bind("<Configure>",self.resize)
		self.root.bind("<KeyPress-i>", self.toggleImage)
		self.root.bind("<KeyPress-f>", self.addMinute) # forward one minute
		self.root.bind("<KeyPress-v>", self.subtractMinute) # reverse one minute
		self.root.bind("<space>", self.resetTime) # reset minutes
		self.root.bind("<KeyPress-F>", self.addHour) # forward one hour
		self.root.bind("<KeyPress-V>", self.subtractHour) # reverse one hour

		
		self.canvas.pack(fill=BOTH, expand=YES) # ???

		if useThread:
		   st=makeThread(self.poll)
		   st.debug = True
		   st.start()
		else:
		   self.poll()

	## Called when the window changes, by means of a user input.
	#
	def resize(self,event):
		sc = self.canvas
		sc.delete(ALL)            # erase the whole canvas
		width  = sc.winfo_width() # get new window width
		height = sc.winfo_height() # get new window height

		imgSize = min(width, height)
		self.pad = imgSize/16 # AHA! padding does scale up with min(w, h)
		viewport = (self.pad,self.pad,width-self.pad,height-self.pad)
		self.T = mapper(self.world,viewport)

		if self.showImage: # nope
		   flu = self.fluImg.resize((int(0.8*0.8*imgSize), int(0.8*imgSize)), Image.ANTIALIAS) 
		   self.flu = ImageTk.PhotoImage(flu)
		   sc.create_image(width/2,height/2,image=self.flu)
		else:
		   self.canvas.create_rectangle([[0,0],[width,height]], fill = self.bgcolor)
		   # Why are we calling create_rectangle(...) all of a sudden?

		self.redraw()             # redraw the clock    

	## Sets the clock colors.
	#
	def setColors(self):
		if self.showImage: # nope
		   self.bgcolor     = 'antique white'
		   self.timecolor   = 'dark orange'
		   self.circlecolor = 'dark green'
		else:
		   self.bgcolor     = '#000000'
		   self.timecolor   = '#ffffff'
		   self.circlecolor = '#e0e0e0' # originally, #808080

	## Toggles the displaying of a background image.
	#
	def toggleImage(self,event):
		if hasPIL and os.path.exists (self.imgPath): # nope
			self.showImage = not self.showImage
			self.setColors()
			self.resize(event)
		

	## Redraws the whole clock.
	# 
	def redraw(self):
		start = pi/2              # 12h is at pi/2 ~ 90*
		step = pi/6               # each step is pi/6 ~ 30*
		for i in range(12):       # draw the minute ticks as circles
			angle =  start-i*step
			x, y = cos(angle),sin(angle)
			self.paintcircle(x,y) # draw number (i) at (x,y)
		self.painthms()           # draw the handles
		if not self.showImage:
		   self.paintcircle(0,0)  # draw a circle at the centre of the clock

	## Set clock forward or back by a given number of minutes
	#
	def seekTime(self, dh = 0, dm = 0):
		self.dMinutes += dm
		self.dHours += dh
		self.redraw()
		
	def addMinute(self, event):
		self.seekTime(dm = 1)
	
	def subtractMinute(self, event):
		self.seekTime(dm = -1)
		
	def addHour(self, event):
		self.seekTime(dh = 1)
		
	def subtractHour(self, event):
		self.seekTime(dh = -1)

	def resetTime(self, event):
		#self.seekTime(dh = -1*self.dHours, dm = -1*self.dMinutes)
		self.dHours = 0
		self.dMinutes = 0
		self.redraw()
		
	## Draws the handles.
	# 
	def painthms(self):
		self.canvas.delete(self._ALL)  # delete the handles
		T = datetime.timetuple(datetime.utcnow()-self.delta)
		x,x,x,h,m,s,x,x,x = T
		m = (m + self.dMinutes) % 60
		h = (h + self.dHours) % 12
		self.root.title('%02i:%02i:%02i' %(h,m,s))
		angle = pi/2 - pi/6 * (h + m/60.0)
		x, y = cos(angle)*0.60,sin(angle)*0.60   
		scl = self.canvas.create_line
		# draw the hour handle
		scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, width = self.pad/3)
		angle = pi/2 - pi/30 * (m + s/60.0)
		x, y = cos(angle)*0.90,sin(angle)*0.90
		# draw the minute handle
		scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, width = self.pad/5)
		angle = pi/2 - pi/30 * s
		x, y = cos(angle)*0.95,sin(angle)*0.95   
		# draw the second handle
		scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, arrow = 'last')
   
	## Draws a circle at a given point.
	# 
	#  @param x,y given point.
	# 
	def paintcircle(self,x,y):
		ss = self.circlesize / 2.0
		sco = self.canvas.create_oval
		sco(self.T.windowToViewport(-ss+x,-ss+y,ss+x,ss+y), fill = self.circlecolor)
  
	## Animates the clock, by redrawing everything after a certain time interval. 
	#
	def poll(self):
		self.redraw()
		self.root.after(200,self.poll)

## Main program for testing.
#
#  @param argv time zone, image background flag,
#         clock width, clock height, create thread flag.
#
def main(argv=None):
	if argv is None:
	   argv = sys.argv
	if len(argv) > 2:
	   try:
		   deltahours = int(argv[1])
		   sImage = (argv[2] == 'True')
		   w = int(argv[3])
		   h = int(argv[4])
		   t = (argv[5] == 'True')
	   except ValueError:
		   print ("A timezone is expected.")
		   return 1
	else:
	   deltahours = 5 # EST
	   sImage = True  
	   w = h = 400
	   t = False

	root = Tk() # TODO: find out what this and the following does
	root.geometry ('+0+0')
	# deltahours: how far are you from utc?
	# Sometimes the clock may be run from another timezone ...
	clock(root,deltahours,sImage,w,h,t)
	root.mainloop() # This officially starts the window and binds its event listeners
	
	# Create a new window
	# With space for the new time

	




	
if __name__=='__main__':
	sys.exit(main())
