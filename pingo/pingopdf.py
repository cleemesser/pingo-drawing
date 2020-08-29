# pingopdf - draws them onto a canvas
"""Usage:
	import pingopdf
	pingopdf.draw(drawing, canvas, x, y)
Execute the script to see some test drawings."""
# Quickest and dirtiest implementation possible, using
# saveState/restoreState to do in Acrobat Reader what we ought to
# be doing here...

# the StateTracker class turned out not to be needed, but I left in
# the calls to it commented.

## to do:
##	  Paths;
##	  careful testing of what happens when stroke and fill are set to None
##	  lots more I have not yet thought of




from pingo import *
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

# hack so we only get warnings once each
warnOnce = WarnOnce()

# the main entry point for users...
def draw(drawing, canvas, x, y):
	"""As it says"""
	R = _PDFRenderer()
	R.draw(drawing, canvas, x, y)


class _PDFRenderer:
	"""This draws onto a PDF document.	It needs to be a class
	rather than a function, as some PDF-specific state tracking is
	needed outside of the state info in the SVG model."""

	def __init__(self):
		self._stroke = 0
		self._fill = 0
		self._tracker = StateTracker()

	def draw(self, drawing, canvas, x, y):
		"""This is the top level function, which
		draws the drawing at the given location.
		The recursive part is handled by drawNode."""
		#stash references for the other objects to draw on
		self._canvas = canvas
		self._drawing = drawing
		try:
			#bounding box
			canvas.rect(x, y, drawing.width, drawing.height)

			#set up coords:
			canvas.saveState()
			canvas.translate(x, y + drawing.height)
			canvas.scale(1, -1)

			# do this gently - no one-liners!
			deltas = drawing.getState()
			self._tracker.push(deltas)
			self.applyStateChanges(deltas, {})

			for node in drawing._data:
				self.drawNode(node)

			self._tracker.pop()
			canvas.restoreState()
		finally:
			#remove any circular references
			del self._canvas, self._drawing

	def drawNode(self, node):
		"""This is the recursive method called for each node
		in the tree"""
		self._canvas.saveState()

		#apply state changes
		deltas = node.getState()
		self._tracker.push(deltas)
		self.applyStateChanges(deltas, {})

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
		elif isinstance(node, NamedReference):
			# drill on down...
			self.drawNode(node.object)
		elif isinstance(node, Group):
			for childNode in node._data:
				self.drawNode(childNode)
		elif isinstance(node, UserNode0):
			self.drawNode(node.provideNode(self))
		else:
			print 'DrawingError','Unexpected element %s in pingo drawing!' % str(node)

		self._tracker.pop()
		self._canvas.restoreState()

	def drawRect(self, rect):
		if rect.rx == rect.ry == 0:
			#plain old rectangle
			self._canvas.rect(
					rect.x, rect.y,
					rect.width, rect.height,
					stroke=self._stroke,
					fill=self._fill
					)
		else:
			#cheat and assume ry = rx; better to generalize
			#pdfgen roundRect function.  TODO
			self._canvas.roundRect(
					rect.x, rect.y,
					rect.width, rect.height, rect.rx,
					fill=self._fill,
					stroke=self._stroke
					)

	def drawLine(self, line):
		if self._stroke:
			self._canvas.line(line.x1, line.y1, line.x2, line.y2)

	def drawCircle(self, circle):
			self._canvas.circle(
					circle.cx, circle.cy, circle.r,
					fill=self._fill,
					stroke=self._stroke
					)

	def drawPolyLine(self, polyline):
		if self._stroke:
			assert len(polyline.points) >= 2, 'Polyline must have 2 or more points'
			head, tail = polyline.points[0:2], polyline.points[2:],
			path = self._canvas.beginPath()
			path.moveTo(head[0], head[1])
			for i in range(0, len(tail), 2):
				path.lineTo(tail[i], tail[i+1])
			self._canvas.drawPath(path)

	def drawEllipse(self, ellipse):
		#need to convert to pdfgen's bounding box representation
		x1 = ellipse.cx - ellipse.rx
		x2 = ellipse.cx + ellipse.rx
		y1 = ellipse.cy - ellipse.ry
		y2 = ellipse.cy + ellipse.ry
		self._canvas.ellipse(x1,y1,x2,y2,fill=1)

	def drawPolygon(self, polygon):
		assert len(polygon.points) >= 2, 'Polyline must have 2 or more points'
		head, tail = polygon.points[0:2], polygon.points[2:],
		path = self._canvas.beginPath()
		path.moveTo(head[0], head[1])
		for i in range(0, len(tail), 2):
			path.lineTo(tail[i], tail[i+1])
		path.close()
		self._canvas.drawPath(
							path,
							stroke=self._stroke,
							fill=self._fill
							)

	def drawString(self, stringObj):
		if self._fill:
			S = self._tracker.getState()
			text_anchor, x, y, text = S['text_anchor'], stringObj.x,stringObj.y,stringObj.text
			if not text_anchor in ['start','inherited']:
				font, font_size = S['font_family'], S['font_size'] 
				textLen = stringWidth(text, font,font_size)
				if text_anchor=='end':
					x = x-textLen
				elif text_anchor=='middle':
					x = x - textLen/2
				else:
					raise ValueError, 'bad value for text_anchor '+str(text_anchor)
			#flip vertical before and after
			self._canvas.addLiteral('BT 1 0 0 -1 %0.2f %0.2f Tm (%s) Tj ET' % (x, y, text))

	def drawPath(self, path):
		warnOnce('Warning: _PDFRendered.drawPath Not Done Yet')

	def applyStateChanges(self, delta, newState):
		"""This takes a set of states, and outputs the PDF operators
		needed to set those properties"""
		for key, value in delta.items():
			if key == 'transform':
				self._canvas.transform(value[0], value[1], value[2],
								 value[3], value[4], value[5])
			elif key == 'stroke':
				#this has different semantics in PDF to SVG;
				#we always have a color, and either do or do
				#not apply it; in SVG one can have a 'None' color
				if value is None:
					self._stroke = 0
				else:
					self._stroke = 1
					self._canvas.setStrokeColor(value)
			elif key == 'stroke_width':
				self._canvas.setLineWidth(value)
			elif key == 'stroke_linecap':  #0,1,2
				self._canvas.setLineCap(value)
			elif key == 'stroke_linejoin':
				self._canvas.setLineJoin(value)
#			 elif key == 'stroke_dasharray':
#				 self._canvas.setDash(array=value)
			elif key == 'stroke_dasharray':
				if value:
					self._canvas.setDash(value)
				else:
					self._canvas.setDash()
			elif key == 'stroke_opacity':
				warnOnce('Stroke Opacity not supported yet')
			elif key == 'fill':
				#this has different semantics in PDF to SVG;
				#we always have a color, and either do or do
				#not apply it; in SVG one can have a 'None' color
				if value is None:
					self._fill = 0
				else:
					self._fill = 1
					self._canvas.setFillColor(value)
			elif key == 'fill_rule':
				warnOnce('Fill rules not done yet')
			elif key == 'fill_opacity':
				warnOnce('Fill opacity not done yet')
			elif key in ['font_size', 'font_family']:
				# both need setting together in PDF
				# one or both might be in the deltas,
				# so need to get whichever is missing
				fontname = delta.get('font_family', self._canvas._fontname)
				fontsize = delta.get('font_size', self._canvas._fontsize)
				self._canvas.setFont(fontname, fontsize)

from reportlab.platypus.layout import Flowable
class PingoFlowable(Flowable):
	"""Flowable wrapper around a Pingo drawing"""
	def __init__(self, PingoDrawing):
		self.drawing = PingoDrawing
		self.width = self.drawing.width
		self.height = self.drawing.height

	def draw(self):
		draw(self.drawing, self.canv, 0, 0)

def drawToFile(d,fn,msg):
	c = Canvas(fn)
	c.setFont('Times-Roman', 36)
	c.drawString(80, 750, msg)

	#print in a loop, with their doc strings
	c.setFont('Times-Roman', 12)
	y = 740
	i = 1
	y = y - d.height
	draw(d, c, 80, y)

	c.save()

#########################################################
#
#	test code.	First, defin a bunch of drawings.
#	Routine to draw them comes at the end.
#
#########################################################


def test():
	c = Canvas('pingopdf.pdf')
	c.setFont('Times-Roman', 36)
	c.drawString(80, 750, 'PINGO Test')

	# print all drawings and their doc strings from the test
	# file

	#grab all drawings from the test module
	import testdrawings
	drawings = []

	for funcname in dir(testdrawings):
		if funcname[0:10] == 'getDrawing':
			drawing = eval('testdrawings.' + funcname + '()')  #execute it
			docstring = eval('testdrawings.' + funcname + '.__doc__')
			drawings.append((drawing, docstring))

	#print in a loop, with their doc strings
	c.setFont('Times-Roman', 12)
	y = 740
	i = 1
	for (drawing, docstring) in drawings:
		if y < 300:  #allows 5-6 lines of text
			c.showPage()
			y = 740
		# draw a title
		y = y - 30
		c.setFont('Times-BoldItalic',12)
		c.drawString(80, y, 'Drawing %d' % i)
		c.setFont('Times-Roman',12)
		y = y - 14
		textObj = c.beginText(80, y)
		textObj.textLines(docstring)
		c.drawText(textObj)
		y = textObj.getY()
		y = y - drawing.height
		draw(drawing, c, 80, y)
		i = i + 1

	c.save()

if __name__=='__main__':
	test()
