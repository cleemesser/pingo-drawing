###############################################################################
#
#	ReportLab Public License Version 1.0
#
#	Except for the change of names the spirit and intention of this
#	license is the same as that of Python
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
#	$Log: pingo.py,v $
#	Revision 1.20  2000/06/06 02:07:18  clee
#	many fixes-- parameters updated and a new check on STATE_PARAMS added
#	(the old one is still there but it doesn't seem to work)
#	
#	Revision 1.19  2000/04/27 03:13:40  clee
#	- fixed bug in moveBy
#	- added path support to pingoArt.py
#	
#	Revision 1.18  2000/04/05 15:21:57  clee
#	provideNodes -> provideNode
#	
#	Revision 1.17  2000/04/02 21:21:19  clee
#	*** empty log message ***
#	
#	Revision 1.16  2000/04/02 20:33:41  clee
#	various UserNode0 stuff
#	
#	Revision 1.15  2000/04/02 19:53:29  clee
#	removed syntax errors
#	
#	Revision 1.14  2000/04/02 19:45:43  clee
#	added UserNode0 and ProtocolNode0, need to provide examples of using both
#	
#	Revision 1.13  2000/04/02 12:15:34  rgbecker
#	Changes for text_anchor
#	
#	Revision 1.12  2000/04/01 00:08:41  clee
#	commented on Path implementation
#	
#	Revision 1.11  2000/03/31 11:52:27  rgbecker
#	Removed 1.5.2 only list pops()
#	
#	Revision 1.10  2000/03/30 09:37:18  rgbecker
#	added RightString, stringLength and forceDefaults
#	
#	Revision 1.9  2000/03/28 14:29:35  rgbecker
#	Fix Drawing.__init__
#	
#	Revision 1.8  2000/03/24 17:24:34  rgbecker
#	Fixed Drawing initialisation bug
#	
#	Revision 1.7  2000/03/24 15:56:26  rgbecker
#	Polygon inheritance was bad
#	
#	Revision 1.6  2000/03/24 15:45:54  rgbecker
#	Fixed Polygon init bug
#	
#	Revision 1.5  2000/03/24 15:38:50  rgbecker
#	Allowed list of 2 tuples in Polygon/PolyLine
#	
#	Revision 1.4  2000/03/24 09:21:47  rgbecker
#	Made Drawing inherit from Group as it should
#	
#	Revision 1.3  2000/03/22 19:11:16  clee
#	sync w/ pingo2
#	
#	Revision 1.5  2000/03/18 23:28:45  clee
#	fixup
#	
#	Revision 1.4  2000/03/18 23:18:20  clee
#	added Hex return value to Paint class
#	
#	Revision 1.3  2000/03/16 12:10:38  rgbecker
#	Various fixes
#	
#	Revision 1.2  2000/03/10 16:06:49  andy_robinson
#	Lots of tidying up throughout.
#
__version__=''' $Id: pingo.py,v 1.20 2000/06/06 02:07:18 clee Exp $ '''


"""
Brain-dead pingo implementation.

The first part of the module defines a class hierarchy to represent
a drawing. This is pure data - it does not do anything at all.

An application programmer will create a Drawing instance and add
shapes, groups and possibly subroutines to it; then get hold of some
function somewhere else to draw it to another object.  Look at the
drawing objects in testdrawings.py to see how they are constructed.

It would be nice to add a validate() routine to check validity of
drawings other applications construct.

At each node, we store only the state variables (fill color, line width
etc.) which are set at that level, in a private dictionary.  It
doesn't even help propagate attributes down, because we have found
no way to do that without walking the tree.

A generic StateTracker utility is provided to keep track of state changes
and unwind them, and a Walker object which can be overridden.  These have not
been used yet, but there is a possibility to optimize the stream of deltas.

"""

from types import ListType, TupleType
from math import cos, sin, tan, pi
import pprint
import colors

try:
	class PingoError(Exception):
		pass
except:
	PingoError = "pingo.error"

def forceDefaults( dict, **kw ):
	'''add keywords from kw to dict if not present'''
	for k in kw.keys():
		if not dict.has_key(k):
			dict[k] = kw[k]

# two filling rules
NON_ZERO_WINDING = 'Non-Zero Winding'
EVEN_ODD = 'Even-Odd'

class Paint:
	"""Introduce a class.  For now it will hold a color
	but one should allow for other color models, gradient
	fills, hatch brushed etc. in future.  For now, take
	an r,g,b tuple."""
	def __init__(self, *stuff):
		if len(stuff) == 3:
			self.paintType = 'Color'
			self.red = stuff[0]
			self.green = stuff[1]
			self.blue = stuff[2]

        def hexRGB():
                if self.paintType == 'Color':
                        r = int(self.red * 0xFF0000)
                        g = int(self.green * 0xFF00)
                        b = int(self.blue * 0xFF)
                        return r+g+b
                return None


# SPEC says: length_unit_specifiers=em, ex, px, pt, pc, cm, mm, in, percentages

#initial coords: 1 unit = 1 'pixel' - call it a point in PDF

STATE_PARAMS =	[# a list of the state params, in readable order
	 'transform',
	 'stroke', 'stroke_width', 'stroke_linecap', 'stroke_linejoin',
         'stroke_miterlimit',
	 'stroke_dasharray', 'stroke_opacity', 
	 'fill', 'fill_rule', 'fill_opacity',
	 'font_family', 'font_size', 'text_anchor' ]

STATE_DEFAULTS = {	 # sensible defaults for all
	'transform': (1,0,0,1,0,0),

	# styles follow SVG naming
	'stroke': colors.black,  #Paint object?
	'stroke_width': 1,
	'stroke_linecap': 0,
	'stroke_linejoin': 0,
        'stroke_miterlimit' : 'TBA',  # don't know yet so let bomb here
	'stroke_dasharray': None,
	'stroke_opacity': 1.0,	#100%

	'fill': colors.black,	#...or text will be invisible
	'fill_rule': NON_ZERO_WINDING,
	'fill_opacity': 1.0,  #100%

	'font_size': 14,
	'font_family': 'Times-Roman',
	'text_anchor':	'start'	# can be start, middle, end, inherited
	}
#check we typed them right...
assert len(STATE_DEFAULTS.keys()) == len(STATE_PARAMS), 'wrong parameters!' # added check-cwl
assert STATE_DEFAULTS.keys().sort() == STATE_PARAMS[:].sort(), 'wrong parameters!'# Hmm.. This doesn't seem to catch error:

class PingoNode:
	"""Base class for all nodes in the tree.  Provides
	accessor methods for all the standard graphics state
	properties which all nodes share, and implements
	the property inheritance feature."""
	#Currently aiming for a copy-down approach to
	#avoid back links and circular references.

	def __init__(self, keywords={}):
		#all state data specified at this level goes in a
		#private dictionary.  Geometry attributes to
		#define the shape will be ordinary python
		#attributes hard coded in subclasses.
		# a dict can be passed in to set up the state
		self._state = {}
		self._setAttrs(keywords)
		self.desc = None
		self.title = None

	def __setattr__(self, key, value):
		# is it a state attribute? if so, in state dict...
		if STATE_DEFAULTS.has_key(key):
			self._state[key] = value
		else:  # otherwise treat as an ordinary attribute
			self.__dict__[key] = value

	def __getattr__(self, key):
		#called only if regular attribute access fails.  See
		#if it is in state dictionary
		return self._state[key]

	def _setAttrs(self,attrs):
		for key, value in attrs.items():
			setattr(self, key, value)

	def getState(self):
		return self._state

	def display(self, indent=''):
		#helpful tracer for seeing drawing structure
		print indent + self.__class__.__name__ + ':'
		attributes = self.__dict__.items()
		attributes.sort()
		for (key, value) in attributes:
			if key <> '_state':
				print '%s	 %s: %s' % (indent, key, value)
		state = self._state.items()
		state.sort()
		for (key, value) in state:
			print '%s	 %s: %s' % (indent, key, value)



	#######################################################
	#
	#	The Primitive Shapes, and a Path; the latter could
	#	represent the primitives, but again this is more
	#	readable and may be faster for other things to draw
	#	Primitive shapes are Rect, Circle, Ellipse, Line,
	#	PolyLine, Polygon
	#
	#######################################################

class Path(PingoNode):
	"""Uses PostScript path model - draw it with
	a succession of moveTo, lineTo operations.
	Each instruction is a tuple beginning with a
	letter indicating the operation type - the same
	letter used by SVG.
	Paths do not make sense without an initial
	point, so start it with a MoveTo"""
	#AR - kept as separate tuples as many back ends
	#would like to see the operations separately,
	#without needing to parse a list of SVG operations.
        #
        # CWL comments:
        # I'm not particularly happy about having each operation a
        # separate tuple.  If i'm drawing a graph I'll have a .moveto(x0, y0)
        # then 1000 points of lineto's all with the same operation
        # Possible solutions:
        #        do as in SVG spec--no tuples, just a long array of letters and numbers
        #        add "LinesTo" type operators which take an array of points

	def __init__(self, x, y, **kw):
		PingoNode.__init__(self, kw)
		self._data = [('M', x, y)]


	def _printdata(self):
		print 'For path:', self
		print self._data


	def moveTo(self, x, y):		   
		self._data.append(('M', x, y))

	def moveBy(self, dx, dy):
		"relative move"
		self._data.append(('m', dx, dy))

	def lineTo(self, x, y):
		self._data.append(('L', x, y))

	def curveTo(self, x1, y1, x2, y2, x, y):
		self._data.append(('C', x1, y1, x2, y2, x, y))

	#need to add all the other curve and arc ops.

class Rect(PingoNode):
	def __init__(self, x, y, width, height, rx=0, ry=0, **kw):
		PingoNode.__init__(self, kw)
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.rx = rx
		self.ry = ry

class Circle(PingoNode):
	def __init__(self, cx, cy, r, **kw):
		PingoNode.__init__(self, kw)
		self.cx = cx
		self.cy = cy
		self.r = r

class Ellipse(PingoNode):
	def __init__(self, cx, cy, rx, ry, **kw):
		PingoNode.__init__(self, kw)
		self.cx = cx
		self.cy = cy
		self.rx = rx
		self.ry = ry

class Line(PingoNode):
	def __init__(self, x1, y1, x2, y2, **kw):
		PingoNode.__init__(self, kw)
		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2

class PolyLine(PingoNode):
	"""Series of line segments.  Does not define a
	closed shape; never filled even if apparently joined.
	Put the numbers in the list, not two-tuples."""
	def __init__(self, points=[], **kw):
		PingoNode.__init__(self, kw)
		lenPoints = len(points)
		if lenPoints:
			if type(points[0]) in (ListType,TupleType):
				L = []
				for (x,y) in points:
					L.append(x)
					L.append(y)
				points = L
			else:
				assert len(points) % 2 == 0, 'Point list must have even number of elements!'
		self.points = points

#class Polygon(PolyLine):
#	"""Defines a closed shape; Is implicitly
#	joined back to the start for you."""
#	def __init__(self, points=[], **kw):
#		apply(PolyLine.__init__,(self, points), kw)
class Polygon(PingoNode):
	"""Defines a closed shape; Is implicitly
	joined back to the start for you."""
	def __init__(self, points=[], **kw):
		PingoNode.__init__(self, kw)
		assert len(points) % 2 == 0, 'Point list must have even number of elements!'
		self.points = points

class String(PingoNode):
	"""Not checked against the spec, just a way to make something work."""
	def __init__(self, x, y, text, **kw):
		PingoNode.__init__(self, kw)
		self.x = x
		self.y = y
		self.text = text


	#######################################################
	#
	#	Groups do most of the work.  They can have a name
	#	and are commonly used to set a transform.
	#######################################################

class Group(PingoNode):
	def __init__(self, *elements, **keywords):
		PingoNode.__init__(self, keywords)
		"""Initial lists of elements may be provided to allow
		compact definitions in literal Python code.  May or
		may not be useful."""
		self._data = []
		for elt in elements:
			self.add(elt)

	def add(self, n):
		'Appends sub node, n'
		if n is not None:
			# propagates properties down
			assert isinstance(n, PingoNode), "Can't add %s to a Group!" % n
			self._data.append(n)

	def insert(self, i, n):
		'inserts sub node, n'
		if n is not None:
			# propagates properties down
			assert isinstance(n, PingoNode), "Can't insert %s in a Group!" % n
			self._data.insert(i,n)

	def display(self, indent=''):
		print indent + 'Group:'
		state = self._state.items()
		state.sort()
		for (key, value) in state:
			print '%s	 %s: %s' % (indent, key, value)
		for element in self._data:
			element.display(indent + '	  ')
	   
class NamedReference(PingoNode):
	"""This is the reuse mechanism.  The name is kept just for
	information, and one could argue that it is a file-level
	thing we don't need in the model.  NamedReference just
	holds a reference to another node, which ought to live
	in the defs dictionary of the drawing."""

	def __init__(self, name, object, **kw):
		PingoNode.__init__(self, kw)
		self.name = name
		self.object = object

class Drawing(Group):
	def __init__(self, width, height, *nodes, **kw):
		self.width = width
		self.height = height

		#names given to groups
		self.defs = {}

		apply(Group.__init__,(self,)+nodes,{})
		#this defines the initial state.
		self._state = STATE_DEFAULTS.copy()
		self._setAttrs(kw)

	def addDef(self, name, group):
		self.defs[name] = group

	def display(self):
		print 'Pingo Drawing'
		print '    width:',self.width
		print '    height:',self.height
		print '    subroutines: ['
		subdata = self.defs.items()
		subdata.sort()
		for (name, group) in subdata:
			print '		   ',name
			group.display(' '*12)
		print '			]'
		print '    drawing elements: ['
		for element in self._data:
			element.display(' '*8)
		print '			]'

# following code convention of using digits at end of constructs that are in testing -cwl
#    Another option would be for a UserNode to be a subclass of a Group() then
# it would set it's state and then produce children.

class UserNode0(PingoNode):

        """A simple template for creating a new node.  The user (Python
        programmer) may subclasses this.  provideNode() must be defined to
        provide a PingoNode primitive when called by a renderer"""

        def __init__(self, **kw):
                PingoNode.__init__(self, kw)
                
        def provideNode(self, sender):
                """Override this to create your own node.  The object that's calling
                this function should provide a reference to itself in sender"""
                # I'm not sure if I want the sender argument here or not. -cwl
                #    Adds flexiblity, but could get complicated.  Maybe should save
                #    for ProtocolNode0
                
                print "Error, this method must be redefined by the user/programmer"
                raise  PingoError


class ProtocolNode0(UserNode0):

        """An opening to provide more sophisticated sorts of nodes.  The node
        requests a certain protocol.  The renderer is expected to check this to
        see if it supports it and let the node know what's going on.  As a
        fallback, is still required to provideNode() if no protocol is supported.

        Might be used to implement communication between the node and the
        renderer based upon a protocol defined by the renderer."""

        def provideProtocols(self):
                raise  PingoError

        # now just need to define a PingoProtocol class
        

#######################################################
#
# define the basic matrix operations here.	We write
# just the six common terms of the 3x3 matrix:
#			(a c e)
#			(b d f)
#			(0 0 1)
# as a six-tuple (a,b,c,d,e,f).   
#######################################################

# constructors for matrices:
def nullTransform():
	return (1, 0, 0, 1, 0, 0)

def translate(dx, dy):
	return (1, 0, 0, 1, dx, dy)

def scale(sx, sy):
	return (sx, 0, 0, sy, 0, 0)

def rotate(angle):
	a = angle * pi /180 
	return (cos(a), sin(a), -sin(a), cos(a), 0, 0)

def skewX(angle):
	a = angle * 180 / pi
	return (1, 0, tan(a), 1, 0, 0)

def skewY(angle):
	a = angle * 180 / pi
	return (1, tan(a), 0, 1, 0, 0)

def mmult(A, B):
	"A postmultiplied by B"
	# I checked this RGB
	# [a0 a2 a4]	[b0 b2 b4]
	# [a1 a3 a5] *	[b1 b3 b5]
	# [		  1]	[		1]
	#
	return (A[0]*B[0] + A[2]*B[1],
			A[1]*B[0] + A[3]*B[1],
			A[0]*B[2] + A[2]*B[3],
			A[1]*B[2] + A[3]*B[3],
			A[0]*B[4] + A[2]*B[5] + A[4],
			A[1]*B[4] + A[3]*B[5] + A[5])

def inverse(A):
	"For A affine 2D represented as 6vec return 6vec version of A**(-1)"
	# I checked this RGB
	det = float(A[0]*A[3] - A[2]*A[1])
	R = [A[3]/det, -A[1]/det, -A[2]/det, A[0]/det]
	return tuple(R+[-R[0]*A[4]-R[2]*A[5],-R[1]*A[4]-R[3]*A[5]])

def zTransformPoint(A,v):
	"Apply the homogenous part of atransformation a to vector v --> A*v"
	return (A[0]*v[0]+A[2]*v[1],A[1]*v[0]+A[3]*v[1])

def transformPoint(A,v):
	"Apply transformation a to vector v --> A*v"
	return (A[0]*v[0]+A[2]*v[1]+A[4],A[1]*v[0]+A[3]*v[1]+A[5])

def transformPoints(matrix, V):
	return map(transformPoint, V)

def zTransformPoints(matrix, V):
	return map(zTransformPoint, V)

class StateTracker:
	"""Keeps a stack of transforms and state
	properties.  It can contain any properties you
	want, but the keys 'transform' and 'ctm' have
	special meanings.  The getCTM()
	method returns the current transformation
	matrix at any point, without needing to
	invert matrixes when you pop."""
	def __init__(self, defaults=None):
		# one stack to keep track of what changes...
		self.__deltas = []

		# and another to keep track of cumulative effects.	Last one in
		# list is the current graphics state.  We put one in to simplify
		# loops below.
		self.__combined = []
		if defaults is None:
			defaults = STATE_DEFAULTS.copy()
		self.__combined.append(defaults)

	def push(self,delta):
		"""Take a new state dictionary of changes and push it onto
		the stack.	After doing this, the combined state is accessible
		through getState()"""

		newstate = self.__combined[-1].copy()
		for (key, value) in delta.items():
			if key == 'transform':	#do cumulative matrix
				newstate['transform'] = delta['transform']
				newstate['ctm'] = mmult(self.__combined[-1]['transform'], delta['transform'])
			else:  #just overwrite it
				newstate[key] = value

		self.__combined.append(newstate)
		self.__deltas.append(delta)

	def pop(self):
		"""steps back one, and returns a state dictionary with the
		deltas to reverse out of wherever you are.	Depending
		on your back endm, you may not need the return value,
		since you can get the complete state afterwards with getState()"""
		del self.__combined[-1]
		newState = self.__combined[-1]
		lastDelta = self.__deltas[-1]
		del  self.__deltas[-1]
		#need to diff this against the last one in the state
		reverseDelta = {}
		for key, curValue in lastDelta.items():
			prevValue = newState[key]
			if prevValue <> curValue:
				if key == 'transform':
					reverseDelta[key] = inverse(lastDelta['transform'])
				else:  #just return to previous state
					reverseDelta[key] = prevValue
		return reverseDelta

	def getState(self):
		"returns the complete graphics state at this point"
		return self.__combined[-1]

	def getCTM(self):
		"returns the current transformation matrix at this point"""
		return self.__combined[-1]['ctm']


def testStateTracker():
	print 'Testing state tracker'
	defaults = {'fill':None, 'stroke':None,'font':None, 'transform':[1,0,0,1,0,0]}
	deltas = [
		{'fill':'red'},
		{'fill':'green', 'stroke':'blue','font':'times'},
		{'transform':[0.5,0,0,0.5,0,0]},
		{'transform':[0.5,0,0,0.5,2,3]},
		{'stroke':'red'}
		]

	st = StateTracker(defaults)
	print 'initial:', st.getState()
	print
	for delta in deltas:
		print 'pushing:', delta
		st.push(delta)
		print 'state:  ',st.getState(),'\n'

	for delta in deltas:
		print 'popping:',st.pop()
		print 'state:  ',st.getState(),'\n'

class Walker:
	"""Base class to override.	The function visit(self, node, state)
	will be called for each node in the drawing.  The function
	stateChange(self, delta, combined) will be called on every
	state change."""
	def walk(self, drawing):
		self.stateStack = StateTracker()
		self.drawing = drawing

		self.stateStack.push(drawing.getState())
		for node in drawing._data:
			self._processNode(node)
		self.stateStack.pop()

		del self.drawing
		del self.stateStack

	def _processNode(self, node):
		delta_in = node.getState()
		self.stateStack.push(delta_in)
		curState = self.stateStack.getState()
		self.stateChange(delta_in, curState)
		self.visit(node, curState)
		if node is Group:
			for child in node._data:
				self._processNode(child)
		elif node is NamedReference:
			name = node.name
			definition = drawing.defs['name']
			self._processNode(definition)

		delta_out = self.stateStack.pop()
		curState = self.stateStack.getState()
		self.stateChange(delta_out, curState)

	def stateChange(self, delta, combined):
		"""Override this to process state changes.
		Delta contains everything which differs;
		combined contains the resulting state.
		Up to you which to use."""
		pass

	def draw(self, node):
		"Override this to draw things"
		pass

class WarnOnce:

	def __init__(self):
		self.uttered = {}

	def once(self,warning):
		if not self.uttered.has_key(warning):
			print 'Warning: ' + warning
			self.uttered[warning] = 1

	def __call__(self,warning):
		self.once(warning)

class TestWalker(Walker):
	"Just lists what it sees..."
	def visit(self, node, state):
		print '\nNODE:', node
		for i in node.__dict__.keys():
			if i =='_state': continue
			print '		 %s = %s' % (i,node.__dict__[i])
		if hasattr(node,'_state') and node._state != {}:
			print '    State:'
			for i in node._state.keys():
				print '		 %s = %s' % (i,node._state[i])

def test():
	D = Drawing(400,400)
	D.add(Circle(100,100,25))
	D.add(Line(10,10,90,90))
	D.add(Rect(0,0,100,100))
	W = TestWalker()
	W.walk(D)
	print 'done'

if __name__=='__main__':
	def testWalk():		   
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
			w = int(drawing.width)
			h = int(drawing.height)
			print '#######################\nDrawing%2d: width=%d height=%d\n%s'% (i,w,h,docstring)
			w = TestWalker()
			w.walk(drawing)
			i = i + 1
	testStateTracker()
	testWalk()
