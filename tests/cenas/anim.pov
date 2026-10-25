#version 3.7;
global_settings { assumed_gamma 1.0 }
#include "colors.inc"
camera { location <0, 3, -6> look_at <0, 1, 0> }
light_source { <4, 8, -6> rgb 1 }
plane { y, 0 pigment { checker rgb 0.85, rgb 0.6 } }
box { <-0.7, 0, -0.7>, <0.7, 1.4, 0.7> pigment { color Red } rotate <0, clock*360, 0> }
