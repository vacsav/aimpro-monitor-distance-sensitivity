import math, BigWorld
from AvatarInputHandler.DynamicCameras import CameraWithSettings
from AvatarInputHandler.DynamicCameras.ArcadeCamera import ArcadeCamera
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.cameras import FovExtended

def overrideIn(cls, condition=lambda : True):

    def _overrideMethod(func):
        if not condition():
            return func
        funcName = func.__name__
        if funcName.startswith('__'):
            funcName = '_' + cls.__name__ + funcName
        old = getattr(cls, funcName)

        def wrapper(*args, **kwargs):
            return func(old, *args, **kwargs)

        setattr(cls, funcName, wrapper)
        return wrapper

    return _overrideMethod


@overrideIn(SniperCamera)
def update(func, self, dx, dy, dz, updatedByKeyboard=False):
    cfg = self._cfg
    key_sensitivity = cfg['keySensitivity']
    scroll_sensitivity = cfg['scrollSensitivity']
    arcade_sensitivity = CameraWithSettings._CameraWithSettings__configs[ArcadeCamera.__name__]['sensitivity']
    arcade_fov = FovExtended.instance().actualDefaultVerticalFov
    sniper_fov = BigWorld.projection().fov
    aspect_ratio = BigWorld.getAspectRatio()
    tan_sniper = math.tan(sniper_fov / 2) * aspect_ratio
    tan_arcade = math.tan(arcade_fov / 2) * aspect_ratio
    sensitivity = arcade_sensitivity * (math.atan(tan_sniper) / math.atan(tan_arcade))
    self._SniperCamera__curSense = key_sensitivity if updatedByKeyboard else sensitivity
    self._SniperCamera__curScrollSense = key_sensitivity if updatedByKeyboard else scroll_sensitivity
    dx_dy_dz = (dx, dy, dz) if updatedByKeyboard else (0, 0, 0)
    self._SniperCamera__autoUpdateDxDyDz.set(*dx_dy_dz)
    if not updatedByKeyboard:
        self._SniperCamera__rotateAndZoom(dx, dy, dz)
