import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0
    name: str = ""

    def distance(self, other):
        # 2D distance, height is ignored
        return math.hypot(other.x - self.x, other.y - self.y)


@dataclass(frozen=True)
class Line:
    start: Point
    end: Point

    def length(self):
        return self.start.distance(self.end)

    def side(self, p):
        # > 0 if p is left of the line, < 0 if right, 0 if on it
        return ((self.end.x - self.start.x) * (p.y - self.start.y)
                - (p.x - self.start.x) * (self.end.y - self.start.y))

    def crosses(self, other):
        # only true for a real crossing, touching at an endpoint doesn't count
        return (self.side(other.start) * self.side(other.end) < 0
                and other.side(self.start) * other.side(self.end) < 0)


@dataclass(frozen=True)
class Triangle:
    a: Point
    b: Point
    c: Point

    def signed_area(self):
        # positive if a, b, c are counter clockwise
        return 0.5 * Line(self.a, self.b).side(self.c)

    def area(self):
        # Heron's formula, from the three side lengths
        a = self.b.distance(self.c)
        b = self.c.distance(self.a)
        c = self.a.distance(self.b)
        s = (a + b + c) / 2
        # max with 0 because rounding can make it slightly negative for flat triangles
        return math.sqrt(max(0.0, s * (s - a) * (s - b) * (s - c)))

    def centroid(self):
        return Point((self.a.x + self.b.x + self.c.x) / 3, (self.a.y + self.b.y + self.c.y) / 3)

    def in_circumcircle(self, d):
        # is d inside the circle through a, b and c
        ax, ay = self.a.x - d.x, self.a.y - d.y
        bx, by = self.b.x - d.x, self.b.y - d.y
        cx, cy = self.c.x - d.x, self.c.y - d.y
        det = ((ax**2 + ay**2) * (bx * cy - cx * by)
               - (bx**2 + by**2) * (ax * cy - cx * ay)
               + (cx**2 + cy**2) * (ax * by - bx * ay))
        # det > 0 means inside for a counter clockwise triangle, so correct for orientation
        return det * self.signed_area() > 0

    def coords(self):
        return [(p.x, p.y) for p in (self.a, self.b, self.c)]


class Triangulation:
    # Triangles between a fixed list of points. Triangles are stored as index
    # triples (counter clockwise) and edges maps an edge {a, b} (frozenset of
    # two indices) to the triangles that have it.

    def __init__(self, points):
        self.points = list(points)
        self.triangles = set()
        self.edges = {}

    def triangle(self, t):
        a, b, c = t
        return Triangle(self.points[a], self.points[b], self.points[c])

    def line(self, e):
        a, b = tuple(e)
        return Line(self.points[a], self.points[b])

    def add(self, a, b, c):
        if self.triangle((a, b, c)).signed_area() < 0:
            b, c = c, b
        self.triangles.add((a, b, c))
        for e in (frozenset((a, b)), frozenset((b, c)), frozenset((c, a))):
            self.edges.setdefault(e, set()).add((a, b, c))

    def remove(self, t):
        self.triangles.remove(t)
        a, b, c = t
        for e in (frozenset((a, b)), frozenset((b, c)), frozenset((c, a))):
            self.edges[e].remove(t)
            if not self.edges[e]:
                del self.edges[e]

    def is_inner_edge(self, e):
        # inner edges have a triangle on both sides
        return len(self.edges.get(e, ())) == 2

    def neighbours(self, e):
        # the two triangles next to edge e and their corners opposite to e
        t1, t2 = self.edges[e]
        c = [v for v in t1 if v not in e][0]
        d = [v for v in t2 if v not in e][0]
        return t1, t2, c, d

    def can_flip(self, e):
        # only possible if the quad around e is convex, i.e. the diagonals cross
        c, d = self.neighbours(e)[2:]
        return self.line(e).crosses(self.line((c, d)))

    def flip(self, e):
        # replace edge a-b by the other diagonal c-d, returns the new edge
        a, b = tuple(e)
        t1, t2, c, d = self.neighbours(e)
        self.remove(t1)
        self.remove(t2)
        self.add(c, d, a)
        self.add(d, c, b)
        return frozenset((c, d))

    def is_delaunay(self, e):
        # an edge is Delaunay if the opposite corner isn't inside the circumcircle
        t1, _, _, d = self.neighbours(e)
        return not self.triangle(t1).in_circumcircle(self.points[d])

    def get_triangles(self):
        return [self.triangle(t) for t in self.triangles]

    @classmethod
    def triangulate(cls, polygon):
        # Constrained Delaunay triangulation, only using the polygon points.
        # 1. normal Delaunay of all points (scipy)
        # 2. flip edges until every polygon edge is in the triangulation (Sloan),
        #    then flip the new edges back to Delaunay where possible (Lawson)
        # 3. throw away the triangles outside the polygon
        polygon.check_simple()
        n = len(polygon.points)

        tri = cls(polygon.points)
        for a, b, c in Delaunay(np.array([(p.x, p.y) for p in polygon.points])).simplices:
            tri.add(int(a), int(b), int(c))

        polygon_edges = {frozenset((i, (i + 1) % n)) for i in range(n)}

        for edge in polygon_edges:
            if edge in tri.edges:
                continue

            # all edges that cross the missing polygon edge
            crossing = [e for e in tri.edges if not (e & edge) and tri.line(edge).crosses(tri.line(e))]
            new_edges = []
            tries = 0
            while crossing:
                e = crossing.pop(0)
                if not tri.can_flip(e):
                    # try again later, other flips can make the quad convex
                    crossing.append(e)
                    tries += 1
                    if tries > 1000:
                        raise ValueError("could not insert polygon edge")
                    continue
                tries = 0
                new = tri.flip(e)
                if not (new & edge) and tri.line(edge).crosses(tri.line(new)):
                    crossing.append(new)
                else:
                    new_edges.append(new)

            # make the new edges Delaunay again (but don't flip polygon edges)
            changed = True
            while changed:
                changed = False
                for i, e in enumerate(new_edges):
                    if e in polygon_edges or not tri.is_inner_edge(e):
                        continue
                    if not tri.is_delaunay(e):
                        new_edges[i] = tri.flip(e)
                        changed = True

        # keep the triangles that are inside the polygon
        return [t for t in tri.get_triangles() if polygon.contains(t.centroid())]


class Polygon:
    def __init__(self, points):
        self.points = list(points)

    def edges(self):
        n = len(self.points)
        return [Line(self.points[i], self.points[(i + 1) % n]) for i in range(n)]

    def contains(self, p):
        # ray casting
        inside = False
        for edge in self.edges():
            p1, p2 = edge.start, edge.end
            if (p1.y > p.y) != (p2.y > p.y):
                if p.x < p1.x + (p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y):
                    inside = not inside
        return inside

    def check_simple(self):
        # the polygon edges can't cross each other
        edges = self.edges()
        n = len(edges)
        for i in range(n):
            for j in range(i + 2, n):
                if (j + 1) % n != i and edges[i].crosses(edges[j]):
                    raise ValueError(f"edge {i}-{i + 1} crosses edge {j}-{(j + 1) % n}")
