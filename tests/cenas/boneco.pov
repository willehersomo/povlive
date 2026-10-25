#version 3.7;
global_settings { assumed_gamma 1.0 }
#include "colors.inc"
#include "cor.inc"

camera { location <0, 3, -7> look_at <0, 1.2, 0> }
light_source { <4, 8, -6> rgb 1 }
background { rgb <0.55, 0.7, 0.9> }
plane { y, 0 pigment { checker rgb 0.85, rgb 0.6 } }

#declare Bola = sphere { <0, 0, 0>, 1 }

union {
    object { Bola scale 0.8 translate <0, 0.8, 0> }
    object { Bola scale 0.55 translate <0, 2, 0> }
    sphere { <0, 2.85, 0>, 0.35 }
    pigment { color White }
}
cone {
    <0, 2.85, -0.3>, 0.08, <0, 2.85, -0.75>, 0
    pigment { CorNariz }
}
box {
    <-0.5, 0, -0.5>, <0.5, 1, 0.5>
    pigment { color Blue }
    rotate <0, 45, 0>
    translate <2.5, 0, 0>
}
