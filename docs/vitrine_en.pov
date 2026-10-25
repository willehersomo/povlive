// Showcase scene used for the README screenshots
#version 3.7;
global_settings { assumed_gamma 1.0 }
#include "colors.inc"
#include "metals.inc"

camera {
    location <0, 3.2, -7.5>
    look_at <0, 1, 0>
}
light_source {
    <5, 9, -6> rgb 1
    area_light <2, 0, 0>, <0, 0, 2>, 4, 4 adaptive 1 jitter
}
light_source { <-6, 5, -3> rgb 0.3 shadowless }
background { rgb <0.55, 0.7, 0.9> }
plane { y, 0 pigment { checker rgb 0.85, rgb 0.6 } }

// die: intersection of a box and a sphere, minus the pips
difference {
    intersection {
        box { -1, 1 }
        sphere { 0, 1.4 }
    }
    sphere { <0, 0, -1.15>, 0.3 }
    sphere { <-0.45, 1.15, -0.45>, 0.25 }
    sphere { <0.45, 1.15, 0.45>, 0.25 }
    pigment { color White }
    finish { phong 0.5 }
    rotate <0, 25, 0>
    translate <-2.2, 1, 0.5>
}

// glass sphere
sphere {
    <0, 1, -0.5>, 1
    pigment { rgbf <0.9, 1, 0.95, 0.95> }
    finish { specular 0.6 reflection 0.1 }
    interior { ior 1.5 }
}

// ring of metal spheres
#for (i, 0, 9)
    sphere { <1, 0.25, 0>, 0.25
        texture { T_Gold_3C }
        rotate <0, i*36, 0>
        translate <2.3, 0, 0.8>
    }
#end

// vase made with lathe
lathe {
    cubic_spline 9,
    <0, 0>, <0.8, 0>, <1, 0.3>, <0.6, 1>, <0.4, 1.6>, <0.7, 2.2>, <0.75, 2.4>, <0.7, 2.4>, <0.6, 2.3>
    pigment { color rgb <0.3, 0.5, 0.9> }
    finish { phong 0.8 reflection 0.1 }
    translate <0.6, 0, 3>
}
