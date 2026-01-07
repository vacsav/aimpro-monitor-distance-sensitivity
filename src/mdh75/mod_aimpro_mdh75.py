import math, BigWorld
from AvatarInputHandler.DynamicCameras import CameraWithSettings, createCrosshairMatrix
from AvatarInputHandler.DynamicCameras.ArcadeCamera import ArcadeCamera
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.cameras import FovExtended


def overrideIn(cls, condition=lambda: True):

    def _overrideMethod(func):
        if not condition():
            return func

        funcName = func.__name__

        if funcName.startswith("__") and funcName != "__init__":
            funcName = "_" + cls.__name__ + funcName

        old = getattr(cls, funcName)

        def wrapper(*args, **kwargs):
            return func(old, *args, **kwargs)

        setattr(cls, funcName, wrapper)
        return wrapper
    return _overrideMethod


orig_init = SniperCamera.__init__
def mod_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.__aspectRatio = None
    self.__arcadeSensitivity = None
    self.__sensitivityMultiplier = 1.0
SniperCamera.__init__ = mod_init


@overrideIn(SniperCamera)
def update(func, self, dx, dy, dz, updatedByKeyboard=False):
    self.__arcadeSensitivity = CameraWithSettings._CameraWithSettings__configs[ArcadeCamera.__name__]['sensitivity']
    self._SniperCamera__curSense = self._cfg['keySensitivity'] if updatedByKeyboard else self.__arcadeSensitivity * self.__sensitivityMultiplier
    self._SniperCamera__curScrollSense = self._cfg['keySensitivity'] if updatedByKeyboard else self._cfg['scrollSensitivity']
    if updatedByKeyboard:
        self._SniperCamera__autoUpdateDxDyDz.set(dx, dy, dz)
    else:
        self._SniperCamera__autoUpdateDxDyDz.set(0, 0, 0)
        self._SniperCamera__rotateAndZoom(dx, dy, dz)


@overrideIn(SniperCamera)
def __updateCrosshairMatrix(func, self):
    if self.__arcadeSensitivity is None:
        self.__arcadeSensitivity = CameraWithSettings._CameraWithSettings__configs[ArcadeCamera.__name__]['sensitivity']    
    self.__aspectRatio = BigWorld.getAspectRatio() * 0.75
    arcadeFov = FovExtended.instance().actualDefaultVerticalFov
    currentFov = BigWorld.projection().fov
    tanCurrentFov = math.tan(currentFov / 2)
    tanSniper = tanCurrentFov * self.__aspectRatio
    tanArcade = math.tan(arcadeFov / 2) * self.__aspectRatio
    self.__sensitivityMultiplier = math.atan(tanSniper) / math.atan(tanArcade)
    curClipPlaneScale = tanCurrentFov
    aimMarkerDistance = self._SniperCamera__aimMarkerDistance * self._DEFAULT_CLIP_PLANE_SCALE / curClipPlaneScale
    self._SniperCamera__crosshairMatrix = createCrosshairMatrix(offsetFromNearPlane=aimMarkerDistance)