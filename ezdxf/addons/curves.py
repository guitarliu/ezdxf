# Purpose: curve objects
# Created: 26.03.2010, 2018 adapted for ezdxf
# Copyright (c) 2010-2018, Manfred Moitzi
# License: MIT License
from __future__ import unicode_literals
from math import sin, cos, radians, fmod
from abc import abstractmethod

from ezdxf.lldxf import const
from ezdxf.algebra.vector import Vector
from ezdxf.algebra.base import rotate_2d, equals_almost
from ezdxf.algebra.cspline import CubicSpline
from ezdxf.algebra.spline import RBSpline, BSpline
from ezdxf.algebra.bezier4p import Bezier4P
from ezdxf.algebra.clothoid import Clothoid as _ClothoidValues
from .mixins import SubscriptAttributes


def vadd(vector1, vector2):
    return vector1[0] + vector2[0], vector1[1] + vector2[1]


class _BaseCurve(SubscriptAttributes):
    @abstractmethod
    def render(self, layout):
        pass


class Ellipse(_BaseCurve):
    def __init__(self, center=(0., 0., 0.), rx=1.0, ry=1.0,
                 startangle=0., endangle=360., rotation=0., segments=100,
                 color=const.BYLAYER, layer='0', linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.center = center
        self.rx = float(rx)
        self.ry = float(ry)
        self.startangle = float(startangle)
        self.endangle = float(endangle)
        self.rotation = float(rotation)
        self.segments = int(segments)

    def render(self, layout):
        def curve_point(alpha):
            alpha = radians(alpha)
            point = (cos(alpha) * self.rx,
                     sin(alpha) * self.ry)
            point = rotate_2d(point, radians(self.rotation))
            x, y = vadd(self.center, point)
            return x, y, zaxis

        def normalize_angle(angle):
            angle = fmod(angle, 360.)
            if angle < 0:
                angle += 360.
            return angle

        zaxis = 0. if len(self.center) < 3 else self.center[2]
        points = []
        delta = (self.endangle - self.startangle) / self.segments
        for segment in range(self.segments):
            alpha = self.startangle + delta * segment
            points.append(curve_point(alpha))

        attribs = {
            'color': self.color,
            'layer': self.layer,
            'linetype': self.linetype,
            'closed': equals_almost(self.startangle, normalize_angle(self.endangle)),
        }
        layout.add_polyline2d(points, dxfattribs=attribs)


class Bezier(_BaseCurve):
    """
    Bezier 2d/3d curve.

    The Bezier() class is implemented with multiple segments, each segment is an optimized 4 point bezier curve, the
    4 control points of the curve are: the start point (1) and the end point (4), point (2) is start point + start vector
    and point (3) is end point + end vector. Each segment has its own approximation count.

    """

    class Segment(object):
        def __init__(self, start, end, start_tangent, end_tangent, segments):
            self.start = Vector(start)
            self.end = Vector(end)
            self.start_tangent = Vector(start_tangent)  # as vector, from start point
            self.end_tangent = Vector(end_tangent)  # as vector, from end point
            self.segments = segments

        def approximate(self):
            control_points = [
                self.start,
                self.start + self.start_tangent,
                self.end + self.end_tangent,
                self.end,
            ]
            bezier = Bezier4P(control_points)
            return bezier.approximate(self.segments)

    def __init__(self, color=const.BYLAYER, layer='0', linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.points = []

    def start(self, point, tangent):
        """
        Set start point and start tangent.

        Args:
            point: start point
            tangent: start tangent as vector, example: (5, 0, 0) means a
                     horizontal tangent with a length of 5 drawing units
        """
        self.points.append((point, None, tangent, None))

    def append(self, point, tangent1, tangent2=None, segments=20):
        """
        Append a control point with two control tangents.

        Args:
            point: the control point
            tangent1: first control tangent as vector *left* of point
            tangent2: second control tangent as vector *right* of point, if omitted tangent2 = -tangent1
            segments: count of line segments for polyline approximation, count of line segments from previous
            control point to this point.

        """
        tangent1 = Vector(tangent1)
        if tangent2 is None:
            tangent2 = -tangent1
        else:
            tangent2 = Vector(tangent2)
        self.points.append((point, tangent1, tangent2, int(segments)))

    def _build_bezier_segments(self):
        if len(self.points) > 1:
            for from_point, to_point in zip(self.points[:-1], self.points[1:]):
                start_point = from_point[0]
                start_tangent = from_point[2]  # tangent2
                end_point = to_point[0]
                end_tangent = to_point[1]  # tangent1
                count = to_point[3]
                yield Bezier.Segment(start_point, end_point,
                                     start_tangent, end_tangent, count)
        else:
            raise ValueError('Two or more points needed!')

    def render(self, layout, force3d=False):
        """
        Render curve as DXF POLYLINE entity.

        Args:
            layout: ezdxf layout object
            force3d: force 3d polyline rendering

        """
        points = []
        for segment in self._build_bezier_segments():
            points.extend(segment.approximate())

        attribs = {
            'layer': self.layer,
            'color': self.color,
            'linetype': self.linetype,
        }
        if force3d or any(p[2] for p in points):
            layout.add_polyline3d(points, dxfattribs=attribs)
        else:
            layout.add_polyline2d(points, dxfattribs=attribs)


class Spline(_BaseCurve):
    """
    Cubic 2d spline.
    """

    def __init__(self, points=None, segments=100, color=const.BYLAYER, layer='0',
                 linetype=None):
        if points is None:
            points = []
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.points = points
        self.segments = int(segments)

    def render(self, layout):
        """
        Render a cubic Spline as 2d polyline. Definition points are fit points.

        Args:
            layout: ezdxf layout

        """
        spline = CubicSpline(self.points)
        layout.add_polyline2d(
            list(spline.approximate(self.segments)),
            dxfattribs={
                'layer': self.layer,
                'color': self.color,
                'linetype': self.linetype,
            }
        )
    render_fit_points = render

    def render_bspline(self, layout):
        """
        Render a BSpline as 3d polyline. Definition points are control points.

        Args:
            layout: ezdxf layout

        """
        spline = BSpline(self.points)
        layout.add_polyline3d(
            list(spline.approximate(self.segments)),
            dxfattribs={
                'layer': self.layer,
                'color': self.color,
                'linetype': self.linetype,
            }
        )

    def render_rbspline(self, layout, weights=None):
        """
        Render a rational BSpline as 3d polyline.

        Args:
            layout: ezdxf layout
            weights: list of weights, requires a weight value for each defpoint.

        """
        if weights is None:
            weights = [1.] * len(self.points)

        spline = RBSpline(self.points, weights)
        layout.add_polyline3d(
            list(spline.approximate(self.segments)),
            dxfattribs={
                'layer': self.layer,
                'color': self.color,
                'linetype': self.linetype,
            }
        )


class Clothoid(_BaseCurve):
    def __init__(self, start=(0, 0), rotation=0., length=1., paramA=1.0,
                 mirror='', segments=100, color=const.BYLAYER, layer='0',
                 linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.start = start
        self.rotation = float(rotation)
        self.length = float(length)
        self.paramA = float(paramA)
        self.mirrorx = 'x' in mirror.lower()
        self.mirrory = 'y' in mirror.lower()
        self.segments = int(segments)

    def render(self, layout):
        def transform(points):
            for point in points:
                if self.mirrorx:
                    point = (point[0], -point[1])
                if self.mirrory:
                    point = (-point[0], point[1])
                point = rotate_2d(point, rotation)
                x, y = vadd(self.start, point)
                yield (x, y, zaxis)

        zaxis = 0. if len(self.start) < 3 else self.start[2]
        rotation = radians(self.rotation)
        clothoid = _ClothoidValues(self.paramA)
        points = clothoid.approximate(self.length, self.segments)
        layout.add_polyline3d(
            list(transform(points)),
            dxfattribs={
                'layer': self.layer,
                'color': self.color,
                'linetype': self.linetype,
            }
        )