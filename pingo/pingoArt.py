# PingoArt.py
# A first attempt at interfacing PyArt libary with pingo2
#     Based upon pingopdf.py with peeks at Robin's pingoGD.py
#     (c) Christopher Lee 2000
# ToDo:
#     - add font changes
#     - round rect implementation
#     - add winding rule/stroke line options
#     - update when PyArt does clipping, dash arrays
#     - implement text_anchor check and state for drawString

from pingo import *
import colors
#from pingo2 import *
import PyArt


# hack so we only get warnings once each
warnOnce = WarnOnce()

def myColor2Hex(colorobj):
    assert isinstance(colorobj, colors.Color)
    r = int(0xFF*colorobj.red) << 16
    g = int(0xFF*colorobj.green) << 8
    b = int(0xFF*colorobj.blue)
    return r+g+b

# the main entry point for users...        
def draw(drawing, canvas, x, y):
    """As it says"""
    R = _ArtRenderer()
    R.draw(drawing, canvas, x, y)

class _ArtRenderer:

    def __init__(self):
        self._stroke = 1
        self._fill = 0

    def draw(self, drawing, canvas, x, y):
        """This is the top level function, which
        draws the drawing at the given location.
        The recursive part is handled by drawNode."""

        self._canvas = canvas
        self._drawing = drawing
        
        # set up coords
        canvas.gsave() # save previous coord state
        canvas.translate(x, y)

        deltas = drawing.getState()
        self.applyStateChanges(deltas, {})

        for node in drawing._data:
            self.drawNode(node)

        canvas.grestore() # matches "save previous coord state"


    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""

        # test to see if there are any changes (this is a win on testdrawings)
        if node._state:
            self._canvas.gsave()
            #apply state changes        
            deltas = node.getState()
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
        elif isinstance(node, UserNode0): # experimental UserNode addition
            print "Attempting to draw a UserNode0"
            self.drawNode(node.provideNode(sender=self))

        else:
            print 'DrawingError','Unexpected element %s in pingo drawing!' % str(node)

        if node._state:
            self._canvas.grestore()



    def fillstrokepath(self, path):
        # fill first, then stroke so that can see the stroked borders
        if self._fill == 1:
            self._canvas.fill(path)
        if self._stroke ==1:
            self._canvas.stroke(path)


    def drawRect(self, rect):
        if rect.rx == rect.ry == 0:
            #plain old rectangle, draw clockwise (x-axis to y-axis) direction
            p = PyArt.VectorPath(6)
            p.moveto_closed(rect.x, rect.y)
            p.lineto(rect.x+rect.width, rect.y)
            p.lineto(rect.x+rect.width, rect.y + rect.height)
            p.lineto(rect.x, rect.y + rect.height)
            p.close()
            self.fillstrokepath(p)
        else:
            bp = PyArt.BezierPath(20)
            bp.rect(rect.x,rect.y, rect.width, rect.height, rect.rx, rect.ry)
            self.fillstrokepath(bp)
            
 
    def drawLine(self, line):
        if self._stroke:
            p = PyArt.VectorPath(3)
            p.moveto_open(line.x1, line.y1)
            p.lineto(line.x2, line.y2)
            self._canvas.stroke(p)

    def drawCircle(self, circle):
        # use the C function for this
        bp = PyArt.BezierPath(12)
        bp.circle(circle.cx,circle.cy, circle.r)
        #  p = self._canvas.circle_path(circle.cx, circle.cy, circle.r)
        self.fillstrokepath(bp)
        #warnOnce("need to implement circle")


    def drawEllipse(self, ellipse):
        bp = PyArt.BezierPath(12)
        bp.ellipse(ellipse.cx, ellipse.cy, ellipse.rx, ellipse.ry)
        self.fillstrokepath(bp)



    def drawPolyLine(self, polyline):
        # improve to use path.lines(..) call ?
        if self._stroke: 
            assert len(polyline.points) >= 2, 'Polyline must have 2 or more points'
            head, tail = polyline.points[0:2], polyline.points[2:], 
            p = PyArt.VectorPath()
            p.moveto_open(head[0], head[1])
            for i in range(0, len(tail), 2):
                p.lineto(tail[i], tail[i+1])
            self._canvas.stroke(p)

    
    def drawPolygon(self, polygon):
        assert len(polygon.points) >= 2, 'Polyline must have 2 or more points'
        head, tail = polygon.points[0:2], polygon.points[2:], 
        p = PyArt.VectorPath(len( polygon.points) +2 ) # actually, should be len(polygon.points)/2 +2 or something

        p.moveto_closed(head[0], head[1])
        for i in range(0, len(tail), 2):
            p.lineto(tail[i], tail[i+1])
        p.close()
        self.fillstrokepath(p)

    def drawString(self, stringObj):
        #flip vertical before and after
        self._canvas.drawString(stringObj.x, stringObj.y, stringObj.text) # assuming that want y-axis flipped

    def drawPath(self, path):
        #p = artPathFromPingoPath(path)
        #self.fillstrokepath(p)
        #warnOnce('Warning: _ArtRenderer.drawPath Not Done Yet')
        p = PyArt.BezierPath(len(path._data))
        pnum = 0  # use to keep track of "close" path actions and go back and reset those moveto_open to _closed
        openlist = []
        closed = 0 # flag to tell me if path has been closed
        for action in path._data:
            if action[0] == 'M':
                p.moveto_open(action[1], action[2])
                curpt = (action[1],action[2])
                openlist.append(pnum)
            elif action[0] == 'm':
                (x,y) = (curpt[0] + action[1], curpt[1]+action[2])
                p.moveto_open(x,y)
                curpt = (x,y)
                openlist.append(pnum)
            elif action[0] == 'L':
                p.lineto(action[1], action[2])
                curpt = (action[1],action[2])
            elif action[0] == 'l':
                (x,y) = (curpt[0] + action[1], curpt[1]+action[2])
                p.lineto(x,y)
                curpt = (x,y)
            elif action[0] == 'C':
                p.curveto(action[1],action[2], action[3], action[4], action[5], action[6])
                curpt = (action[5], action[6])
            pnum = pnum +1
        self.fillstrokepath(p)
                

    def applyStateChanges(self, delta, newState):
        """This takes a set of states, and outputs the PDF operators
        needed to set those properties"""
        for key, value in delta.items():
            if key == 'transform':
                # note SVG/pingo2's affine representation switches role of b and c vs PyArt's
                self._canvas.transform(value[0], value[2], value[1], value[3], value[4], value[5])

            elif key == 'stroke':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                if value is None:
                    self._stroke = 0
                else:
                    self._stroke = 1
                    self._canvas.gstate.stroke = myColor2Hex(value) #  setStrokeColor(value)
            elif key == 'stroke_width':
                self._canvas.gstate.stroke_width = value
            elif key == 'stroke_linecap':  #0,1,2
                self._canvas.gstate.stroke_linecap = value # this is just guessing these values match up ???
            elif key == 'stroke_linejoin':
                self._canvas.gstate.stroke_linejoin = value
            elif key == 'stroke_dasharray':
                warnOnce("PyArt doesn't yet implement dash arrays ")
                #self._canvas.setDash(array=value)
            elif key == 'stroke_opacity':
                self._canvas.gstate.stroke_opacity = value
            elif key == 'fill':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                if value is None:
                    self._fill = 0
                else:
                    self._fill = 1
                    self._canvas.gstate.fill = myColor2Hex(value)
            elif key == 'fill_rule':
                warnOnce('Fill rules not done yet')
            elif key == 'fill_opacity':
                self._canvas.gstate.fill_opacity = value
            elif key in ['font_size', 'font_family']:
                # both need setting together in PDF
                # one or both might be in the deltas,
                # so need to get whichever is missing
                warnOnce("I don't deal with font changes yet")
                #fontname = delta.get('font_family', self._canvas._fontname)
                #fontsize = delta.get('font_size', self._canvas._fontsize)
                #self._canvas.setFont(fontname, fontsize)


    #########################################################
    #
    #   test code.  First, defin a bunch of drawings.
    #   Routine to draw them comes at the end.
    #
    #########################################################

if __name__=='__main__':



    def test():
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

        # do the first test
        c = PyArt.Canvas(512,212) # may want dpi=96 or so
        c.gstate.fill = 0x000000
        c.gstate.stroke = 0xFFFFFF

        x = 10
        y = 10

        lineheight = 20
        drawingNum = 1

        for (drawing, docstring) in drawings:

            c.clear(0xFFFFFF)
            filename = "pingoArt_test%d.png" % drawingNum

            draw(drawing, c, x, y)

            #c.drawString(x, y, "Drawing %d" % drawingNum)
            #c.drawString(x, y, docstring)
            drawingNum = drawingNum + 1

            c.save(filename)
    

    test()
    # my quickie profiling
    #import profile
    #profile.run('test()', 'test.profile')
    #import pstats
    #p = pstats.Stats('test.profile')
    #p.strip_dirs()
    #p.sort_stats('time')
    #p.print_stats()
    #p.sort_stats('cum')
    #p.print_stats()












