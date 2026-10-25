"""English version of the POV-Ray guide (same structure and example ids as guia.TOPICOS)."""

TOPICOS = [
    # ------------------------------------------------------------------
    ("1. First steps", [
        ("txt", """<p>A POV-Ray scene is a text file that describes <b>what exists</b> and
<b>where we look from</b>. POV-Ray then does <i>ray tracing</i>: for each pixel, it shoots a ray from the camera
and computes the color of whatever it hits.</p>
<p>Every scene needs three things:</p>
<ol><li>a <b>camera</b> – where we look from and where to;</li>
<li><b>light</b> – without light, everything is black;</li>
<li><b>objects</b> – with some <code>pigment</code> (color), otherwise they are black too.</li></ol>"""),
        ("ex", "inicio", """sphere {
    <0, 1, 0>, 1          // center and radius
    pigment { color Red }  // color (Red comes from colors.inc)
}""", {}),
        ("txt", """<p><b>Basic syntax:</b></p>
<ul><li>vectors are written between <code>&lt; &gt;</code>: <code>&lt;x, y, z&gt;</code>;</li>
<li>blocks go between braces: <code>sphere { ... }</code>;</li>
<li><code>//</code> comments until the end of the line and <code>/* ... */</code> comments a section;</li>
<li><code>#include "colors.inc"</code> brings ready-made color names (Red, White, SkyBlue...);</li>
<li>a color is <code>rgb &lt;r, g, b&gt;</code> with values from 0 to 1; <code>rgb 1</code> is white.</li></ul>"""),
        ("txt", """<h3>Coordinate system</h3>
<p>POV-Ray uses a <b>left-handed</b> system: <b>x</b> to the right, <b>y</b> up and
<b>z into the screen</b> (away from the viewer). Turn on the axes with <b>Ctrl+E</b>:
x is red, y is green and z is blue.</p>"""),
        ("ex", "coords", """// A sphere at the tip of each positive axis
sphere { <2, 0.3, 0>, 0.3 pigment { color Red } }    // +x (right)
sphere { <0, 2, 0>, 0.3 pigment { color Green } }    // +y (up)
sphere { <0, 0.3, 2>, 0.3 pigment { color Blue } }   // +z (into the screen)
sphere { <0, 0.3, 0>, 0.15 pigment { color White } } // origin""",
         {"camera": "camera {\n    location <2.5, 3, -4>\n    look_at <0.4, 0.6, 0.4>\n}"}),
        ("dica", "Common mistakes: forgetting a closing brace <code>}</code>, forgetting the comma between a vector "
                 "and a number (<code>&lt;0,1,0&gt;, 1</code>) and wrong capitalization (<code>red</code> ≠ "
                 "<code>Red</code>)."),
    ]),
    # ------------------------------------------------------------------
    ("2. Camera", [
        ("txt", """<p><code>location</code> is where the camera is and <code>look_at</code> is the point it aims at.
<code>angle</code> sets the horizontal field of view in degrees (default ≈ 67°): smaller is zoom/telephoto,
larger is wide-angle.</p>"""),
        ("ex", "cam_angle", """// Try angle 30 (zoom) and angle 100 (wide-angle)
camera {
    location <0, 3, -7>
    look_at <0, 1, 0>
    angle 50
}
sphere { <0, 1, 0>, 1 pigment { color Orange } }
box { <-3, 0, 2>, <-2, 2, 3> pigment { color SkyBlue } }
box { <2, 0, 2>, <3, 2, 3> pigment { color SkyBlue } }""",
         {"camera": "// (the camera is in the example itself; the last camera in the scene is the one used)"}),
        ("txt", """<p>The <b>orthographic</b> camera has no perspective: far objects are the same size as near ones.
It is the projection of technical drawings (front, top and side views). <code>right</code> and <code>up</code>
say how many units fit in the width and the height.</p>"""),
        ("ex", "cam_orto", """camera {
    orthographic
    location <0, 1, -10>
    look_at <0, 1, 0>
    right x*8*image_width/image_height   // 8 units tall, proportional width
    up y*8
}
// both boxes are the same size, but the one at the back is much farther away
box { <-2.5, 0, 0>, <-0.5, 2, 1> pigment { color Red } }
box { <0.5, 0, 15>, <2.5, 2, 16> pigment { color Blue } }""", {"camera": ""}),
        ("dica", "In the app: <b>F6</b> turns on the free camera (drag on the image to orbit) and <b>Shift+F6</b> "
                 "copies the chosen position into the code. <b>F7</b> shows the front, top and side views."),
    ]),
    # ------------------------------------------------------------------
    ("3. Lights", [
        ("txt", """<p><code>light_source { position color }</code> creates a point light, which shines in every
direction and casts hard shadows. The light itself is invisible: we only see its effect.</p>"""),
        ("ex", "luz_ponto", """light_source { <-3, 4, -2> color rgb <1, 0.6, 0.3> }  // extra orange light
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("txt", """<p><b>area_light</b> is a light with an area (a rectangle of lights), which makes <b>soft
shadows</b>. The two vectors are the sides of the rectangle and the numbers say how many lights there are
along each side.</p>"""),
        ("ex", "luz_area", """light_source {
    <2, 6, -3> rgb 1
    area_light <3, 0, 0>, <0, 0, 3>, 6, 6   // 3x3 rectangle with 6x6 lights
    adaptive 1 jitter                       // faster and without "steps" in the shadow
}
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("txt", """<p><b>spotlight</b> is a flashlight: it lights a cone. <code>radius</code> is the angle of the
fully lit part and <code>falloff</code> is the angle where the light ends.</p>"""),
        ("ex", "luz_spot", """light_source {
    <0, 6, 0> color rgb <1, 1, 0.8>
    spotlight
    point_at <0, 0, 0>
    radius 12
    falloff 20
}
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("dica", "<code>shadowless</code> makes a light that casts no shadow. It is useful as a fill light "
                 "to brighten the dark parts (the examples' setting uses one)."),
    ]),
    # ------------------------------------------------------------------
    ("4. Basic solids", [
        ("txt", """<p>Primitives are defined by a few numbers. Hover over the name of each one in the editor to
see its syntax.</p>
<table border=0 cellspacing=6>
<tr><td><code>sphere { center, radius }</code></td><td>sphere</td></tr>
<tr><td><code>box { corner1, corner2 }</code></td><td>axis-aligned box (two opposite corners)</td></tr>
<tr><td><code>cylinder { base, top, radius }</code></td><td>cylinder between two points</td></tr>
<tr><td><code>cone { base, radius1, top, radius2 }</code></td><td>cone or truncated cone</td></tr>
<tr><td><code>torus { major_radius, minor_radius }</code></td><td>donut lying on the XZ plane</td></tr>
<tr><td><code>plane { normal, distance }</code></td><td>infinite plane</td></tr>
<tr><td><code>disc { center, normal, radius }</code></td><td>thin disc</td></tr></table>"""),
        ("ex", "solidos", """sphere   { <-3, 1, 0>, 1                      pigment { color Red } }
box      { <-1.5, 0, -0.5>, <-0.5, 1.5, 0.5>   pigment { color Orange } }
cylinder { <0.5, 0, 0>, <0.5, 2, 0>, 0.5        pigment { color Yellow } }
cone     { <2.2, 0, 0>, 0.7, <2.2, 2, 0>, 0     pigment { color Green } }
torus    { 0.8, 0.25 translate <4.2, 0.25, 0>   pigment { color Blue } }""",
         {"camera": "camera {\n    location <0.5, 4, -9>\n    look_at <0.5, 0.8, 0>\n}"}),
        ("txt", """<p>A <b>cone</b> with both radii different from zero becomes a <b>truncated cone</b>. The word
<code>open</code> removes the caps of the cylinder and the cone, leaving only the wall.</p>"""),
        ("ex", "tronco", """cone { <-1.5, 0, 0>, 1, <-1.5, 1.5, 0>, 0.5 pigment { color Cyan } }        // truncated cone
cylinder { <1.5, 0, 0>, <1.5, 1.5, 0>, 0.8 open pigment { color Magenta } }  // no caps""", {}),
    ]),
    # ------------------------------------------------------------------
    ("5. Advanced solids", [
        ("txt", """<p><b>prism</b> extrudes (stretches) a 2D polygon along y. The points are &lt;x, z&gt; and
the polygon must end at the same point where it started.</p>"""),
        ("ex", "prisma", """prism {
    linear_sweep
    0, 1,          // from y=0 to y=1
    6,             // number of points
    <-1, -1>, <1, -1>, <1.5, 0.5>, <0, 1.5>, <-1.5, 0.5>, <-1, -1>
    pigment { color Gold }
}""", {}),
        ("txt", """<p><b>lathe</b> is a solid of revolution: you draw a profile &lt;radius, height&gt; and it spins
around the y axis, like on a lathe. Great for vases, cups and chess pawns.</p>"""),
        ("ex", "torno", """lathe {
    cubic_spline
    9,
    <0, 0>, <0.8, 0>, <1, 0.3>, <0.6, 1>, <0.4, 1.6>, <0.7, 2.2>, <0.75, 2.4>, <0.7, 2.4>, <0.6, 2.3>
    pigment { color rgb <0.3, 0.5, 0.9> }
    finish { phong 0.8 }
}""", {}),
        ("txt", """<p><b>text</b> makes 3D text from a TrueType font. The numbers are the thickness and an
offset between letters.</p>"""),
        ("ex", "texto", """text {
    ttf "timrom.ttf" "POV-Ray" 0.3, 0
    pigment { color Red }
    scale 1.2
    translate <-2.3, 0.2, 0>
}""", {}),
        ("txt", """<p><b>blob</b> objects are "metaballs": spheres that merge smoothly when they are close, like
drops.</p>"""),
        ("ex", "blob", """blob {
    threshold 0.6
    sphere { <-0.7, 1, 0>, 1.2, 1 }
    sphere { < 0.7, 1, 0>, 1.2, 1 }
    sphere { < 0, 1.8, 0>, 0.9, 1 }
    pigment { color rgb <0.2, 0.8, 0.4> }
    finish { phong 0.9 }
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("6. Transformations", [
        ("txt", """<p>Every object accepts three basic transformations. <b>All of them happen relative to the
origin &lt;0,0,0&gt; and the world axes</b>, not to the center of the object:</p>
<ul><li><code>translate &lt;dx, dy, dz&gt;</code> moves;</li>
<li><code>rotate &lt;ax, ay, az&gt;</code> rotates in degrees around x, then y, then z;</li>
<li><code>scale &lt;sx, sy, sz&gt;</code> (or <code>scale s</code>) stretches or shrinks from the origin.</li></ul>"""),
        ("ex", "translate", """// the same box, original and moved
box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> pigment { color White } }
box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> pigment { color Red } translate <2, 0, 1> }""", {}),
        ("txt", """<h3>Which way does rotate turn?</h3>
<p><b>Left-hand</b> rule: point your left thumb to the positive side of the axis; your curled fingers show
the positive direction. In practice: <b>looking from the positive tip of the axis toward the origin, a
positive angle turns clockwise</b>.</p>
<p>Careful: the default front camera sits at negative z looking toward +z, so it looks
<i>from behind</i> the z axis. That is why, to it, <code>rotate &lt;0, 0, 45&gt;</code> looks
<b>counterclockwise</b>. (Checked in POV-Ray: <code>rotate &lt;0,0,90&gt;</code> takes the x axis to y.)</p>"""),
        ("ex", "rotate", """// pointer aiming at +x; change the 45 by Ctrl+dragging it
#declare Pointer = union {
    box { <0, -0.08, -0.08>, <2, 0.08, 0.08> }
    cone { <2, 0, 0>, 0.25, <2.5, 0, 0>, 0 }
}
object { Pointer pigment { color White } translate <0, 1.5, 0> }               // original
object { Pointer pigment { color Red } rotate <0, 0, 45> translate <0, 1.5, 0> } // rotated""",
         {"camera": "camera {\n    location <0, 1.5, -7>\n    look_at <0, 1.5, 0>\n}", "chao": ""}),
        ("txt", """<p><code>scale</code> with different values on each axis deforms the object: a sphere becomes
an ellipsoid. A <b>negative</b> value mirrors (reflects) the object along that axis.</p>"""),
        ("ex", "scale", """// sphere stretched in x and squashed in y: it becomes an ellipsoid
sphere { <0, 0, 0>, 1 pigment { color Yellow } scale <1.5, 0.5, 1> translate <-4, 0.5, 0> }

// mirroring: scale <-1, 1, 1> flips the sign of x, reflecting across the plane x = 0
#declare L = union { box { <0.5, 0, 0>, <0.8, 2, 0.3> } box { <0.5, 0, 0>, <1.6, 0.3, 0.3> } }
object { L pigment { color Blue } }                     // original (positive x)
object { L pigment { color Cyan } scale <-1, 1, 1> }    // reflected (negative x)
box { <-0.02, 0, -1>, <0.02, 2.4, 1> pigment { rgbt <1, 1, 1, 0.5> } } // the "mirror" at x = 0""",
         {"camera": "camera {\n    location <-1, 3, -7>\n    look_at <-1, 1, 0>\n}"}),
    ]),
    # ------------------------------------------------------------------
    ("7. Order of transformations", [
        ("txt", """<p>Transformations are applied <b>in the order they appear</b>, and the order changes the
result. Since <code>rotate</code> and <code>scale</code> work around the origin:</p>
<ul><li><b>rotate, then translate</b>: the object spins around itself (it was at the origin) and then moves
into place;</li>
<li><b>translate, then rotate</b>: the object has already left the origin, so it <b>orbits</b> around it.</li></ul>"""),
        ("ex", "ordem", """#declare MyBox = box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> }
// green: spins in place, then moves to x=2
object { MyBox pigment { color Green } rotate <0, 45, 0> translate <2, 0, 0> }
// red: moves to x=2, then rotates around the ORIGIN
object { MyBox pigment { color Red }   translate <2, 0, 0> rotate <0, 45, 0> }
// references: the origin and the circle of radius 2
cylinder { <0, 0, 0>, <0, 1.5, 0>, 0.06 pigment { color White } }
torus { 2, 0.03 pigment { color Yellow } }""",
         {"camera": "camera {\n    location <1, 6, -5>\n    look_at <1, 0, 0>\n}"}),
        ("txt", """<h3>Rotating around any point</h3>
<p>To rotate around a point P: move P to the origin, rotate and move it back.
It is the same idea as composite matrices: <code>T(P) · R · T(−P)</code>.</p>"""),
        ("ex", "pivo", """// door with its hinge at x=1: rotates around the point <1, 0, 0>
#declare Door = box { <-1, 0, 0>, <1, 2.5, 0.1> }
object { Door pigment { color rgb 0.6 } }   // closed (reference)
object { Door pigment { color Brown }
    translate <-1, 0, 0>   // hinge goes to the origin
    rotate <0, -60, 0>     // opens
    translate <1, 0, 0>    // back into place
}""", {"camera": "camera {\n    location <0, 4, -6>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<h3>matrix: any affine transformation</h3>
<p><code>matrix &lt;a,b,c, d,e,f, g,h,i, tx,ty,tz&gt;</code> applies a 3x3 matrix plus a translation.
The point (x, y, z) becomes <code>(a·x + d·y + g·z + tx, b·x + e·y + h·z + ty, c·x + f·y + i·z + tz)</code>,
so each row of 3 numbers is where one axis goes. It is useful, for example, for <b>shearing</b>, which
cannot be done with rotate/scale.</p>"""),
        ("ex", "matrix", """// shear: the higher, the more it shifts in x (x' = x + 0.5*y)
box { <-0.5, 0, -0.5>, <0.5, 2, 0.5>
    pigment { color Violet }
    matrix < 1,   0, 0,     // where the x axis goes
             0.5, 1, 0,     // where the y axis goes (tilted)
             0,   0, 1,     // where the z axis goes
             0,   0, 0 >    // translation
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("8. Composition (CSG)", [
        ("txt", """<p>CSG (<i>Constructive Solid Geometry</i>) combines solids with set operations:</p>
<table border=0 cellspacing=6>
<tr><td><code>union { A B }</code></td><td>A ∪ B: joins everything into one object</td></tr>
<tr><td><code>difference { A B }</code></td><td>A − B: removes from A whatever is inside B</td></tr>
<tr><td><code>intersection { A B }</code></td><td>A ∩ B: only the part that is in both</td></tr>
<tr><td><code>merge { A B }</code></td><td>like union, but without the inner walls (better for glass)</td></tr></table>
<p>Transformations and textures placed at the end apply to the whole set.</p>"""),
        ("ex", "csg3", """#declare A = box { <-0.8, -0.8, -0.8>, <0.8, 0.8, 0.8> }
#declare B = sphere { 0, 1.05 }
union        { object { A } object { B } pigment { color Red }   translate <-3, 1, 0> }
difference   { object { A } object { B } pigment { color Green } translate < 0, 1, 0> }
intersection { object { A } object { B } pigment { color Blue }  translate < 3, 1, 0> }""",
         {"camera": "camera {\n    location <0, 4, -8>\n    look_at <0, 0.9, 0>\n}"}),
        ("txt", """<p>Classic example: a <b>die</b>. It is the intersection of a box and a sphere (rounded
corners) minus small spheres (the pips).</p>"""),
        ("ex", "dado", """difference {
    intersection {
        box { -1, 1 }        // -1 becomes <-1,-1,-1>
        sphere { 0, 1.4 }
    }
    sphere { <0, 0, -1.15>, 0.3 }                                           // front face: 1
    sphere { <-0.45, 1.15, -0.45>, 0.25 } sphere { <0.45, 1.15, 0.45>, 0.25 } // top: 2
    sphere { <-1.15, 0.45, -0.45>, 0.25 } sphere { <-1.15, 0, 0>, 0.25 }
    sphere { <-1.15, -0.45, 0.45>, 0.25 }                                   // side: 3
    pigment { color White }
    finish { phong 0.5 }
    rotate <0, 30, 0>
    translate <0, 1, 0>
}""", {"camera": "camera {\n    location <-3, 4, -5>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p>To drill a hole: <code>difference</code> with a cylinder longer than the piece (so it goes
all the way through and no thin film is left).</p>"""),
        ("ex", "furo", """difference {
    cylinder { <0, 0, 0>, <0, 1, 0>, 1.5 }                // washer
    cylinder { <0, -0.1, 0>, <0, 1.1, 0>, 0.7 }           // hole, a little taller
    pigment { color rgb <0.7, 0.7, 0.75> }
    finish { phong 0.7 reflection 0.15 }
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("9. Variables, loops and macros", [
        ("txt", """<p><code>#declare Name = ...;</code> stores a number, vector, color, texture or object to use
later. Declared objects are used with <code>object { Name }</code>, and each use can have its own
transformations and colors.</p>"""),
        ("ex", "declare", """#declare Radius = 0.4;
#declare Snowman = union {
    sphere { <0, Radius, 0>, Radius }
    sphere { <0, Radius*2.5, 0>, Radius*0.7 }
}
object { Snowman pigment { color White } translate <-1.5, 0, 0> }
object { Snowman pigment { color Pink } }
object { Snowman pigment { color Cyan } scale 1.5 translate <1.8, 0, 0> }""", {}),
        ("txt", """<p><code>#for (i, start, end)</code> repeats a section. With it, geometric patterns become
short: a row of spheres, a ring, a spiral staircase.</p>"""),
        ("ex", "for_anel", """// 12 spheres in a circle: each one goes to x=2 and rotates i*30° in y
#for (i, 0, 11)
    sphere { <2, 0.3, 0>, 0.3
        pigment { color rgb <i/11, 0.4, 1 - i/11> }
        rotate <0, i*30, 0>
    }
#end""", {}),
        ("ex", "for_escada", """// spiral staircase: each step goes up and rotates a little more
#for (i, 0, 19)
    box { <0.3, 0, -0.25>, <1.8, 0.1, 0.25>
        pigment { color rgb <0.8, 0.6, 0.4> }
        rotate <0, i*20, 0>
        translate <0, i*0.2, 0>
    }
#end
cylinder { <0, 0, 0>, <0, 4.2, 0>, 0.3 pigment { color White } }""",
         {"camera": "camera {\n    location <0, 6, -7>\n    look_at <0, 1.8, 0>\n}"}),
        ("txt", """<p><code>#macro</code> is a function that builds objects from parameters.</p>"""),
        ("ex", "macro", """#macro Tree(Height, Col)
    union {
        cylinder { <0, 0, 0>, <0, Height*0.4, 0>, 0.1 pigment { color Brown } }
        cone { <0, Height*0.3, 0>, Height*0.3, <0, Height, 0>, 0 pigment { color Col } }
    }
#end
object { Tree(2, ForestGreen) translate <-2, 0, 0> }
object { Tree(3, Green) }
object { Tree(1.5, YellowGreen) translate <2, 0, 0.5> }""", {}),
    ]),
    # ------------------------------------------------------------------
    ("10. Colors and textures", [
        ("txt", """<p>The look of an object has four parts, which can go together inside <code>texture { }</code>:</p>
<ul><li><code>pigment</code> – the color or the color pattern;</li>
<li><code>finish</code> – how the surface reacts to light (matte, shiny, mirror);</li>
<li><code>normal</code> – fake bumps (dents, waves);</li>
<li><code>interior</code> – what happens inside (refraction, for glass and water).</li></ul>
<p>Use <b>Ctrl+Shift+C</b> with the cursor on an <code>rgb</code> to pick the color from a palette.</p>"""),
        ("ex", "padroes", """// checker
sphere { <-3, 1, 0>, 0.9
    pigment { checker color Red, color White scale 0.3 }
}
// gradient along y
sphere { <-1, 1, 0>, 0.9
    pigment { gradient y color_map { [0 color Blue] [1 color Yellow] } }
}
// marble (turbulence scrambles the pattern)
sphere { <1, 1, 0>, 0.9
    pigment { marble turbulence 0.8
              color_map { [0 color White] [1 color rgb 0.2] } }
}
// wood (rings around the z axis)
sphere { <3, 1, 0>, 0.9
    pigment { wood scale 0.2
              color_map { [0 color rgb <0.6, 0.35, 0.15>] [1 color rgb <0.35, 0.18, 0.08>] } }
}""",
         {"camera": "camera {\n    location <0, 3, -8>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p><b>finish</b>: <code>ambient</code> is the minimum self-light, <code>diffuse</code> the
scattered light, <code>phong</code>/<code>specular</code> the highlight and <code>reflection</code> the
mirroring.</p>"""),
        ("ex", "finish", """sphere { <-3, 1, 0>, 0.9 pigment { color Red } }                                     // default
sphere { <-1, 1, 0>, 0.9 pigment { color Red } finish { phong 0.9 phong_size 60 } }  // plastic
sphere { < 1, 1, 0>, 0.9 pigment { color rgb 0.1 } finish { reflection 0.8 } }      // mirror
sphere { < 3, 1, 0>, 0.9 pigment { color Red } normal { bumps 0.6 scale 0.15 } }     // bumps""",
         {"camera": "camera {\n    location <0, 3, -8>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p><b>Transparency</b>: <code>rgbf</code> has a 4th value, the <i>filter</i> (transparency that
tints the light), and <code>rgbt</code> has the <i>transmit</i> (transparency that does not tint). For real
glass, use <code>interior { ior 1.5 }</code>: the index of refraction bends the light.</p>"""),
        ("ex", "vidro", """sphere { <0, 1, 0>, 1
    pigment { rgbf <0.9, 1, 0.9, 0.95> }
    finish { specular 0.6 reflection 0.1 }
    interior { ior 1.5 }
}
box { <-0.3, 0, 2>, <0.3, 2.5, 2.3> pigment { color Red } }   // behind it, to see the refraction""", {}),
        ("txt", """<p>The files <code>textures.inc</code>, <code>metals.inc</code>, <code>stones.inc</code> and
<code>woods.inc</code> bring ready-made textures. Include the file and use the name.</p>"""),
        ("ex", "prontas", """sphere { <-2.2, 1, 0>, 0.9 texture { T_Stone8 } }
sphere { < 0, 1, 0>, 0.9 texture { T_Gold_3C } }
sphere { < 2.2, 1, 0>, 0.9 texture { T_Wood10 } }""",
         {"extra_inc": ("textures.inc", "metals.inc", "stones.inc", "woods.inc"),
          "camera": "camera {\n    location <0, 3, -7>\n    look_at <0, 1, 0>\n}"}),
    ]),
    # ------------------------------------------------------------------
    ("11. Animation", [
        ("txt", """<p>The <code>clock</code> variable goes from 0 to 1 over the animation. Use it inside any
number: <code>rotate &lt;0, clock*360, 0&gt;</code> makes a full turn.</p>
<p>In the app: drag the <b>clock</b> bar, press <b>▶</b> to play and use <b>Export GIF</b> (Ctrl+G)
to save the animation.</p>"""),
        ("ex", "anim_gira", """box { <-1, 0, -1>, <1, 1.5, 1>
    pigment { checker color Orange, color White scale 0.5 }
    rotate <0, clock*360, 0>
}""", {}),
        ("txt", """<p>Combining: a ball that <b>bounces</b> (height with <code>abs(sin(...))</code>) while it moves
from one side to the other.</p>"""),
        ("ex", "anim_quica", """#declare Height = abs(sin(clock*2*pi*2)) * 2;    // 2 bounces per cycle
sphere { <0, 0.5 + Height, 0>, 0.5
    pigment { color Red }
    finish { phong 0.8 }
    translate <-3 + 6*clock, 0, 0>
}""", {}),
        ("txt", """<p>You can animate the camera too: here it goes once around the scene.</p>"""),
        ("ex", "anim_camera", """camera {
    location <0, 3, -7>
    look_at <0, 1, 0>
    rotate <0, clock*360, 0>    // rotates the camera around the y axis
}
box { <-0.5, 0, -0.5>, <0.5, 2, 0.5> pigment { color Blue } }
sphere { <1.5, 0.5, 0>, 0.5 pigment { color Red } }
cone { <-1.5, 0, 0>, 0.5, <-1.5, 1.5, 0>, 0 pigment { color Green } }""", {"camera": ""}),
    ]),
    # ------------------------------------------------------------------
    ("12. App tips and common errors", [
        ("txt", """<h3>Working fast</h3>
<ul><li><b>Ctrl + drag</b> on a number changes its value live (hold Shift too for fine control);</li>
<li><b>Ctrl+E</b> turns on the axes and <b>F7</b> shows the front, top and side views: great for checking
positions;</li>
<li><b>Ctrl+P</b> pins the current image to compare before and after; <b>F8</b> shows the version history;</li>
<li>the <b>Insert</b> menu has ready-made templates for objects, lights and textures;</li>
<li><b>Ctrl + click</b> on an <code>#include</code> opens the file in a tab;</li>
<li>resting the mouse on a keyword shows its syntax;</li>
<li><b>clicking an object in the image</b> takes you to its line in the code and shows <b>X/Y/Z arrows</b>
(move along an axis) and a <b>ring</b> (rotate in y); <b>Ctrl + drag</b> on the image moves the object in the
screen plane;</li>
<li>while you drag something, a <b>quick preview</b> in OpenGL appears (no shadows or textures); when you let
go, the POV-Ray render comes in;</li>
<li><b>F9</b> opens the matrix panel: the transformations of the object under the cursor as 4x4 matrices, in
column-vector (textbook) or POV-Ray convention;</li>
<li><b>Ctrl+Shift+F</b> formats the code and <b>Ctrl+Shift+X</b> exports a hand-in package (.zip with scene,
image and GIF);</li>
<li>POV-Ray warnings appear in yellow in the status bar (<b>⚠</b>), some with an automatic fix.</li></ul>
<h3>Frequent error messages</h3>
<table border=0 cellspacing=6>
<tr><td><code>No matching } in ...</code></td><td>a brace was not closed (see the red highlight of the pair)</td></tr>
<tr><td><code>Expected 'numeric expression'</code></td><td>a missing number, or an extra or missing comma in a vector</td></tr>
<tr><td><code>Undeclared identifier 'Xxx'</code></td><td>misspelled name, or the <code>#include</code> that defines it is missing</td></tr>
<tr><td><code>Cannot open include file</code></td><td>wrong file name, or the file is in another folder</td></tr>
<tr><td>all-black image</td><td>no light, a light inside an object or the camera inside an object</td></tr>
<tr><td>object does not show up</td><td>outside the camera view, behind it, hidden in the floor or without <code>pigment</code></td></tr></table>"""),
    ]),
]
