"""Bake source eye layers for the SDK's opaque base-color material. MIT."""
import math
import numpy as np
from PIL import Image


def bake_iris_sclera(iris, sclera, radius, size=1024):
    """Approximate an eye shader's centered UV-radius iris over its sclera.

    Does not reproduce refraction, subsurface scattering or pupil deformation.
    Inputs are retained unmodified; radius comes from source material metadata.
    """
    if not math.isfinite(radius) or not 0 < radius < .5:
        raise ValueError('Invalid source iris UV radius')
    if type(size) is not int or not 16 <= size <= 2048:
        raise ValueError('Eye bake size outside bounds')
    result=sclera.convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
    diameter=max(2,round(2*radius*size))
    layer=iris.convert('RGBA').resize((diameter,diameter),Image.Resampling.LANCZOS)
    y,x=np.mgrid[:diameter,:diameter]
    distance=np.sqrt(((x+.5-diameter/2)/(diameter/2))**2+((y+.5-diameter/2)/(diameter/2))**2)
    mask=Image.fromarray(np.uint8(np.clip((1-distance)*diameter/2,0,1)*255))
    result.paste(layer,((size-diameter)//2,(size-diameter)//2),mask)
    return result
