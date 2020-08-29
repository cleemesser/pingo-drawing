#!/bin/env python
###############################################################################
#
#	ReportLab Public License Version 1.0
#
#   Except for the change of names the spirit and intention of this
#   license is the same as that of Python
#
#	(C) Copyright ReportLab Inc. 1998-2000.
#
#
# All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted, provided
# that the above copyright notice appear in all copies and that both that
# copyright notice and this permission notice appear in supporting
# documentation, and that the name of ReportLab not be used
# in advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.
#
#
# Disclaimer
#
# ReportLab Inc. DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS,
# IN NO EVENT SHALL ReportLab BE LIABLE FOR ANY SPECIAL, INDIRECT
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#
###############################################################################
#	$Log: pingoGD.py,v $
#	Revision 1.8  2000/04/14 12:56:01  rgbecker
#	Usernode0 arg fixes
#	
#	Revision 1.7  2000/04/14 12:47:25  rgbecker
#	provideNodes-->provideNode
#	
#	Revision 1.6  2000/04/02 22:08:45  clee
#	edited drawNode so that a warning is issued instead of an exception
#	when encountering an unrecognized node -cwl
#	
#	Revision 1.5  2000/04/02 12:15:34  rgbecker
#	Changes for text_anchor
#	
#	Revision 1.4  2000/03/31 12:37:28  rgbecker
#	Altered font mapping for non win32 systems
#	
#	Revision 1.3  2000/03/29 08:39:35  rgbecker
#	Corrected drawToString __doc__
#
#	Revision 1.2  2000/03/29 08:33:52  rgbecker
#	Added drawToFile, drawToString
#
#	Revision 1.1  2000/03/22 19:02:00  clee
#	sync with pingo2
#
#	Revision 1.2  2000/03/19 11:38:01  rgbecker
#	Rounded rectangles
#	
__version__=''' $Id: pingoGD.py,v 1.8 2000/04/14 12:56:01 rgbecker Exp $ '''
"""Usage:
	import pingoGD
	pingoGD.draw(drawing, canvas, x, y)
Execute the script to see some test drawings."""
## TODO:
##	  Paths;
##	  careful testing of what happens when stroke and fill are set to None


from pingo import *
import string, os, sys
import gd
if sys.platform == 'win32':
	_fontdir = 'c:/windows/fonts'
else:
	_fontdir = os.path.join(os.path.dirname(__file__),'TTF')

_fontMap	= {	'TIMES-ROMAN':			os.path.join(_fontdir,'TIMES.TTF'),
				'TIMES-ITALIC':			os.path.join(_fontdir,'TIMESI.TTF'),
				'TIMES-BOLD':			os.path.join(_fontdir,'TIMESBD.TTF'),
				'TIMES-BOLDITALIC':		os.path.join(_fontdir,'TIMESBI.TTF'),
				'COURIER':				os.path.join(_fontdir,'COUR.TTF'),
				'COURIER-OBLIQUE':		os.path.join(_fontdir,'COURI.TTF'),
				'COURIER-BOLD':			os.path.join(_fontdir,'COURBD.TTF'),
				'COURIER-BOLDOBLIQUE':	os.path.join(_fontdir,'COURBI.TTF'),
				'HELVETICA':			os.path.join(_fontdir,'ARIAL.TTF'),
				'HELVETICA-OBLIQUE':	os.path.join(_fontdir,'ARIALI.TTF'),
				'HELVETICA-BOLD':		os.path.join(_fontdir,'ARIALBD.TTF'),
				'HELVETICA-BOLDOBLIQUE':os.path.join(_fontdir,'ARIALBI.TTF'),
				'SYMBOL':				os.path.join(_fontdir,'SYMBOL.TTF')}

def _findColor(c,im):
	if c is None: return -1
	rgb = int(c.red*255), int(c.green*255), int(c.blue*255)
	cx = im.colorExact(rgb)
	if cx<0:
		cx=im.colorAllocate(rgb)
		if cx<0:
			cx = im.colorClosest(rgb)
		if cx<0:
			raise PingoError, "Can't allocate color "+str(c)
	return cx

# hack so we only get warnings once each
warnOnce = WarnOnce()

# the main entry point for users...
def draw(drawing, canvas, x, y):
	"""As it says"""
	R = _GDRenderer()
	R.draw(drawing, canvas, x, y)

class _GDRenderer:
	"""This draws onto a GD image.	It needs to be a class
	rather than a function, as some image-specific state tracking is
	needed outside of the state info in the SVG model."""

	def __init__(self):
		self._tracker = StateTracker()

	def pop(self):
		self._tracker.pop()
		self.applyState()

	def push(self,node):
		deltas = node.getState()
		self._tracker.push(deltas)
		self.applyState()

	def applyState(self):
		s = self._tracker.getState()
		try:
			self._im.setTransform(s['ctm'])
		except KeyError:
			self._im.setTransform(None)

		self._im.setDotWidth(s['stroke_width'])

	def getStroke(self):
		return _findColor(self._tracker.getState()['stroke'],self._im)

	def getFill(self):
		return _findColor(self._tracker.getState()['fill'],self._im)

	def getTextAnchor(self):
		return self._tracker.getState()['text_anchor']

	def getFontSize(self):
		return self._tracker.getState()['font_size']

	def getFont(self):
		try:
			font=self._tracker.getState()['font_family']
			return _fontMap[string.upper(font)]
		except KeyError:
			raise PingoError, "Can't map font %s" % font

	def draw(self, drawing, canvas, x, y):
		"""This is the top level function, which
		draws the drawing at the given location.
		The recursive part is handled by drawNode."""
		#stash references for the other objects to draw on
		self._im = canvas._im
		self._drawing = drawing
		try:
			# do this gently - no one-liners!
			self.push(drawing)
			if x or y:
				self._tracker({'transform':translate(x,y)})

			for node in drawing._data:
				self.drawNode(node)

			self.pop()
		finally:
			#remove any circular references
			del self._im, self._drawing

	def drawNode(self, node):
		"""This is the recursive method called for each node
		in the tree"""

		#apply state changes
		self.push(node)

		#draw the object, or recurse
		if isinstance(node, Line):
			self.drawLine(node)
		elif isinstance(node, Rect):
			self.drawRect(node)
		elif isinstance(node, Circle):
			self.drawCircle(node)
		elif isinstance(node, Ellipse):
			self.drawEllipse(node)
		elif isinstance(node, PolyLine):
			self.drawPolyLine(node)
		elif isinstance(node, Polygon):
			self.drawPolygon(node)
		elif isinstance(node, Path):
			self.drawPath(node)
		elif isinstance(node, String):
			self.drawString(node)
		elif isinstance(node, UserNode0):
			self.drawNode(node.provideNode(self))
		elif isinstance(node, NamedReference):
			# drill on down...
			self.drawNode(node.object)
		elif isinstance(node, Group):
			for childNode in node._data:
				self.drawNode(childNode)
		else:
			print 'DrawingError','Unexpected element %s in pingo drawing!' % str(node)

		# restore the state
		self.pop()

	def drawRect(self, rect):
		stroke = self.getStroke()
		fill = self.getFill()
		if stroke<0 and fill<0: return
		x0, x1, y0, y1, rx, ry = rect.x, rect.width, rect.y, rect.height, rect.rx, rect.ry
		x1 = x1+x0
		y1 = y1+y0
		if rx == 0 or ry == 0 or x0==x1 or y0==y1:
			#plain old rectangle
			self._im.rectangle((x0,y0),(x1,y1), stroke, fill)
		else:
			rx = abs(rx)
			ry = abs(ry)
			if y0>y1: y0, y1 = y1, y0
			if x0>x1: x0, x1 = x1, x0
			if fill>=0:
				self._im.filledRectangle((x0,y0+ry), (x1,y1-ry), fill)
				self._im.filledRectangle((x0+rx,y1-ry), (x1-rx,y1), fill)
				self._im.filledRectangle((x0+rx,y0), (x1-rx,y0+ry), fill)
				self._im.arc(pos=(x0+rx, y0+ry), size=(2*rx,2*ry), start=180, end=270,
						color=-1, fill=fill, mode=gd.gdPIE)
				self._im.arc(pos=(x0+rx, y1-ry), size=(2*rx,2*ry), start=90, end=180,
						color=-1, fill=fill, mode=gd.gdPIE)
				self._im.arc(pos=(x1-rx, y1-ry), size=(2*rx,2*ry), start=0, end=90,
						color=-1, fill=fill, mode=gd.gdPIE)
				self._im.arc(pos=(x1-rx, y0+ry), size=(2*rx,2*ry), start=270, end=360,
						color=-1, fill=fill, mode=gd.gdPIE)
			if stroke>=0:
				self._im.line((x0,y0+ry), (x0,y1-ry), stroke)
				self._im.line((x1,y0+ry), (x1,y1-ry), stroke)
				self._im.line((x0+rx,y0), (x1-rx,y0), stroke)
				self._im.line((x0+rx,y1), (x1-rx,y1), stroke)
				self._im.arc(pos=(x0+rx, y0+ry), size=(2*rx,2*ry), start=180, end=270,
						color=stroke, fill=-1, mode=gd.gdARC)
				self._im.arc(pos=(x0+rx, y1-ry), size=(2*rx,2*ry), start=90, end=180,
						color=stroke, fill=-1, mode=gd.gdARC)
				self._im.arc(pos=(x1-rx, y1-ry), size=(2*rx,2*ry), start=0, end=90,
						color=stroke, fill=-1, mode=gd.gdARC)
				self._im.arc(pos=(x1-rx, y0+ry), size=(2*rx,2*ry), start=270, end=360,
						color=stroke, fill=-1, mode=gd.gdARC)

	def drawLine(self, line):
		stroke = self.getStroke()
		if stroke>=0:
			self._im.line((line.x1,line.y1),(line.x2,line.y2),stroke)

	def drawCircle(self, circle):
		#gd needs diameters
		self._im.arc(pos=(circle.cx, circle.cy), size=(2*circle.r,2*circle.r), start=0, end=360,
						color=self.getStroke(), fill=self.getFill(), mode=gd.gdPIE)

	def drawPolyLine(self, polyline):
		stroke=self.getStroke()
		if stroke>=0:
			self._im.lines(polyline.points,stroke)

	def drawEllipse(self, ellipse):
		#gd needs diameters
		self._im.arc(pos=(ellipse.cx, ellipse.cy), size=(2*ellipse.rx,2*ellipse.ry), start=0, end=360,
						color=self.getStroke(), fill=self.getFill(), mode=gd.gdPIE)

	def drawPolygon(self, polygon):
		stroke = self.getStroke()
		fill = self.getFill()
		self._im.polygon( polygon.points, stroke, fill )

	def drawString(self, stringObj):
		fill = self.getFill()
		if fill>=0:
			tA = self.getTextAnchor()
			text=stringObj.text
			font=self.getFont()
			pos=(stringObj.x, stringObj.y)
			size=self.getFontSize()*64./72
			if not tA in ['start','inherited']:
				b = self._im.stringTTF(text=text,font=font,pos=pos,size=size,render=0,flipXY=1,fg=fill,trans=0)
				if tA=='end':
					pos=(pos[0]-(b[2]-b[0]), pos[1])
				elif tA=='middle':
					pos=(pos[0]-(b[2]-b[0])/2, pos[1])
				else:
					raise ValueError, 'bad value for text_anchor '+str(tA)

			#flip vertical before and after
			self._im.stringTTF(text=text,font=font,pos=pos,size=size,render=1,flipXY=1,fg=fill,trans=0)

	def drawPath(self, path):
		warnOnce('Warning: _GDRendered.drawPath Not Done Yet')

class GDImage:
	def __init__(self,wh):
		self._im = gd.image(wh)
		white=self._im.colorAllocate((255,255,255))
		black=self._im.colorAllocate((0,0,0))

def drawToFile(d,fn,kind='GIF', quality=-1):
	'''create a GDImage and draw pingo drawing, d to it then save as a file'''
	w = int(d.width)
	h = int(d.height)
	c = GDImage((w,h))
	draw(d, c, 0, 0)
	kind = string.upper(kind)
	if kind=='GIF':
		c._im.writeGif(fn)
	elif kind=='JPG':
		c._im.writeJPG(fn) #, quality=-1)
	elif kind=='PNG':
		c._im.writePNG(fn)

def drawToString(d,kind='GIF'):
	'''create a GDImage and draw pingo drawing, d to it return as string'''
	w = int(d.width)
	h = int(d.height)
	c = GDImage((w,h))
	draw(d, c, 0, 0)
	kind = string.upper(kind)
	if kind=='GIF':
		c._im.getGifBytes(fn)
	elif kind=='JPG':
		c._im.getJPGBytes(fn) #, quality=-1)
	elif kind=='PNG':
		c._im.getPNGBytes(fn)
	else:
		raise ValueError,"Don't understand kind="+kind

if __name__=='__main__':
	#########################################################
	#
	#	test code.	First, define a bunch of drawings.
	#	Routine to draw them comes at the end.
	#
	#########################################################
	def test():
		#grab all drawings from the test module
		import testdrawings
		drawings = []

		for funcname in dir(testdrawings):
			if funcname[0:10] == 'getDrawing':
				drawing = eval('testdrawings.' + funcname + '()')  #execute it
				docstring = eval('testdrawings.' + funcname + '.__doc__')
				drawings.append((drawing, docstring))

		i = 0
		#print in a loop, with their doc strings
		for (drawing, docstring) in drawings:
			if 1:
				w = int(drawing.width)
				h = int(drawing.height)
				print 'Drawing%2d: width=%d height=%d\n%s'% (i,w,h,docstring)
				drawToFile(drawing,'pingoGD%d.gif'%i,kind='gif')
				drawToFile(drawing,'pingoGD%d.jpg'%i,kind='jpg')
				drawToFile(drawing,'pingoGD%d.png'%i,kind='png')
			i = i + 1
	test()
