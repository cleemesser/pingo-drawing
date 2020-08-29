#	Initial version Robin Becker
#	$Log: Affine2D.py,v $
#	Revision 1.2  2000/03/24 07:59:58  rgbecker
#	Added Id + Log
#	
__version__=''' $Id: Affine2D.py,v 1.2 2000/03/24 07:59:58 rgbecker Exp $ '''
'''
The 2 dimensional affine transformation is implemented here using length 6 lists.
'''
from math import tan, sqrt, fabs, pi
from types import ListType, TupleType
eps 	= 2.220446049250313e-016
reps 	= 4503599627370496.0
rooteps	= 1.490116119384766e-008
rrooteps= 67108864.0
class Affine2D:
	def __init__(self,mx=None):
		self._mx = mx

	def __str__(self):
		if self._mx is None: return '(1,0,0,1,0,0)'
		return str(self._mx)

	def __repr__(self):
		return "%s at %x, %s" % (str(self.__class__),id(self),str(self))

	def transformPoint(self,v=(0,0)):
		'Apply self to Point, v --> T(v)'
		assert len(v)==2
		mx = self._mx
		if mx is None: return v
		return mx[0]*v[0]+mx[2]*v[1]+mx[4], mx[1]*v[0]+mx[3]*v[1]+mx[5]

	def transformPoints(self,V):
		'Apply self to list of Points, v --> T(v)'
		return map(lambda x, self=self: self.transformPoint(x), V)

	def zTransformPoint(self,v=(0,0)):
		'Apply self to vector & translate to origin, v --> H(v)'
		assert len(v)==2
		mx = self._mx
		if mx is None: return v
		return mx[0]*v[0]+mx[2]*v[1], mx[1]*v[0]+mx[3]*v[1]

	def zTransformPoints(self,V):
		'Apply self and translate to origin a list of Points, V --> H(v)'
		return map(lambda x, self=self: self.zTransformPoint(x), V)

	def __call__(self,v=(0.0)):
		return self.transformPoint(v)

	def rotate(self,angle=0):
		t = tan(angle*pi/180.0)
		at = fabs(t)
		mx = self._mx
		if at<=eps:
			#c = 1
			#s = 0
			return self
		elif at >= reps:
			#c = 0
			s = t<0 and -1 or 1
			if mx==None: return Affine2D([0, s, -s, 0, 0, 0])
			return Affine2D([mx[2]*s,mx[3]*s, -mx[0]*s, -mx[1]*s, mx[4], mx[5]])
		elif at<rooteps:
			#c = 1
			#s = t
			if mx==None: return Affine2D([ 1, t, -t, 1, 0, 0])
			return Affine2D([mx[0]+mx[2]*t,mx[1]+mx[3]*t, -mx[0]*t+mx[2], -mx[1]*t+mx[3], mx[4], mx[5]])
		elif at > rrooteps:
			c = 1 / at
			s = t<0 and -1 or 1
		else:
			c = 1 /sqrt(at*at+1)
			s = c * t
		if mx==None: return Affine2D([ c, s, -s, c, 0, 0])
		return Affine2D([mx[0]*c+mx[2]*s,mx[1]*c+mx[3]*s, -mx[0]*s+mx[2]*c, -mx[1]*s+mx[3]*c, mx[4], mx[5]])

	def translate(self,tx,ty):
		mx = self._mx
		if mx == None: return Affine2D([1,0,0,1,tx,ty])
		return Affine2D(mx[0:4]+[mx[0]*tx+mx[2]*ty+mx[4],mx[1]*tx+mx[3]*ty+mx[5]])

	def translateX(self,tx):
		mx = self._mx
		if mx == None: return Affine2D([1,0,0,1,tx,0])
		return Affine2D(mx[0:4]+[mx[0]*tx+mx[4],mx[1]*tx+mx[5]])

	def translateY(self,ty):
		mx = self._mx
		if mx == None: return Affine2D([1,0,0,1,0,ty])
		return Affine2D(mx[0:4]+[mx[2]*ty+mx[4],mx[3]*ty+mx[5]])

	def scale(self,sx,sy):
		mx = self._mx
		if mx == None: return Affine2D([sx,0,0,sy,0,0])
		return Affine2D([sx*mx[0],sx*mx[1],sy*mx[2],sy*mx[3],mx[4],mx[5]])

	def scaleX(self,sx):
		mx = self._mx
		if mx == None: return Affine2D([sx,0,0,1,0,0])
		return Affine2D([sx*mx[0],sx*mx[1]]+mx[2:])

	def scaleY(self,sy):
		mx = self._mx
		if mx == None: return Affine2D([1,0,0,sy,0,0])
		return Affine2D([mx[0],mx[1],sy*mx[2],sy*mx[3],mx[4],mx[5]])

	def skewX(self,angle):
		t = tan(angle*pi/180.0)
		mx = self._mx
		if mx == None: return Affine2D([1,0,t,1,0,0])
		return Affine2D([mx[0],mx[1],mx[0]*t+mx[2],mx[1]*t+mx[3],mx[4],mx[5]])

	def skewY(self,angle):
		t = tan(angle*pi/180.0)
		mx = self._mx
		if mx == None: return Affine2D([1,t,0,1,0,0])
		return Affine2D([mx[0]+mx[2]*t,mx[1]+mx[3]*t]+mx[2:])

	def inverse(self):
		"return the inverse transform"
		# I checked this RGB
		A = self._mx
		if A is None: return self
		det = float(A[0]*A[3] - A[2]*A[1])
		R = [A[3]/det, -A[1]/det, -A[2]/det, A[0]/det]
		return Affine2D(R+[-R[0]*A[4]-R[2]*A[5],-R[1]*A[4]-R[3]*A[5]])

	def transform(self,T):
		'general transformation applied to self'
		if type(T) in [TupleType, ListType]: T= Affine2D(T)
		assert T.__class__ is Affine2D
		A = self._mx
		if A is None: return T
		else:
			B = T._mx
			if B is None: return self
			else:
				# I checked this RGB
				# [a0 a2 a4]	[b0 b2 b4]
				# [a1 a3 a5] *	[b1 b3 b5]
				# [		  1]	[		1]
				#
				return Affine2D((A[0]*B[0] + A[2]*B[1],
								A[1]*B[0] + A[3]*B[1],
								A[0]*B[2] + A[2]*B[3],
								A[1]*B[2] + A[3]*B[3],
								A[0]*B[4] + A[2]*B[5] + A[4],
								A[1]*B[4] + A[3]*B[5] + A[5]))
if __name__=='__main__':
	mx = Affine2D()
	print 'init',	`mx`
	print '+45',	`mx.rotate(45)`
	print '-45',	`mx.rotate(-45)`
	print '+90',	`mx.rotate(90)`
	print '-90',	`mx.rotate(-90)`
	print '+180',	`mx.rotate(+180)`
	print '-180',	`mx.rotate(-180)`
	print '+360',	`mx.rotate(+360)`
	print '-360',	`mx.rotate(-360)`
	print '-90+90', `mx.rotate(-90).rotate(90)`
	print 'tx+10', `mx.translate(10,0)`
	print 'tx+10 rot+45 tx-10', `mx.translate(10,0).rotate(45).translate(-10,0)`
	print 'rot+45([1,0])',	`mx.rotate(45)([1,0])`
	print 'rot+45.scl(0.5,1)([1,0])',	`mx.rotate(45).scale(0.5,1)([1,0])`
	print 'rot+45.scl(0.5,1).rot-45([1,0])',	`mx.rotate(45).scale(0.5,1).rotate(-45)([1,0])`
	print 'rot+45.inverse', `mx.rotate(45).inverse()`
	print 'rot+45.inverse.transform(rot+45)', `mx.rotate(45).inverse().transform(mx.rotate(45))`
