import os, json, math, BigWorld
import AvatarInputHandler.DynamicCameras
from AvatarInputHandler.DynamicCameras import CameraWithSettings, createCrosshairMatrix
from AvatarInputHandler.DynamicCameras.ArcadeCamera import ArcadeCamera
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.DynamicCameras.arcade_camera_helper import EScrollDir
from AvatarInputHandler.cameras import FovExtended
from realm import CURRENT_REALM


def isClientLesta():
    return CURRENT_REALM == 'RU'


def isClientWG():
    return not isClientLesta()


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


DEFAULT_CONFIG = {
    "Arcade": {
        "Y_Multiplier": "1.0",
        "X_Multiplier": "1.0",
        "Sensitivity_Multiplier": "1.0"
    },
    "Sniper": {
        "Y_Multiplier": "1.0",
        "X_Multiplier": "1.0",
        "Sensitivity_Multiplier": "1.0"
    }
}

CONFIG_PATH = os.path.join('mods', 'configs', 'AimPro', 'config.json')
CONFIG_DIR = os.path.dirname(CONFIG_PATH)

def ensureConfigExists():
    if os.path.isfile(CONFIG_PATH):
        return

    try:
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)

        with open(CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

        print('[mod_aimpro_fl] config.json created with defaults')
    except Exception as e:
        print('[mod_aimpro_fl] Failed to create config.json:', e)

def loadConfig():
    ensureConfigExists()

    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        print('[mod_aimpro_fl] Failed to load config.json, using defaults')
        return DEFAULT_CONFIG.copy()

CONFIG = loadConfig()

ARCADE_CFG = CONFIG.get('Arcade', {})
ARCADE_Y_MP  = float(ARCADE_CFG.get('Y_Multiplier', 1.0))
ARCADE_X_MP  = float(ARCADE_CFG.get('X_Multiplier', 1.0))
ARCADE_SENS_MP = float(ARCADE_CFG.get('Sensitivity_Multiplier', 1.0))

SNIPER_CFG = CONFIG.get('Sniper', {})
SNIPER_Y_MP  = float(SNIPER_CFG.get('Y_Multiplier', 1.0))
SNIPER_X_MP  = float(SNIPER_CFG.get('X_Multiplier', 1.0))
SNIPER_SENS_MP = float(SNIPER_CFG.get('Sensitivity_Multiplier', 1.0))


def mod_calcYawPitchDelta(cfg, curSenseX, curSenseY, dx, dy):
    return (dx * curSenseX * (-1 if cfg['horzInvert'] else 1), dy * curSenseY * (-1 if cfg['vertInvert'] else 1))
AvatarInputHandler.DynamicCameras.calcYawPitchDelta = mod_calcYawPitchDelta
calcYawPitchDelta = AvatarInputHandler.DynamicCameras.calcYawPitchDelta


orig_arcade_init = ArcadeCamera.__init__
def mod_arcade_init(self, *args, **kwargs):
    orig_arcade_init(self, *args, **kwargs)
    self._ArcadeCamera__curSenseX = 0
    self._ArcadeCamera__curSenseY = 0
ArcadeCamera.__init__ = mod_arcade_init


orig_sniper_init = SniperCamera.__init__
def mod_sniper_init(self, *args, **kwargs):
    orig_sniper_init(self, *args, **kwargs)
    self.__curSenseX = 0
    self.__curSenseY = 0
    self.__sensitivityMultiplier = 1.0
SniperCamera.__init__ = mod_sniper_init


@overrideIn(ArcadeCamera, condition=isClientLesta)
def update(func, self, dx, dy, dz, rotateMode = True, zoomMode = True, updatedByKeyboard = False):
    cfg = self._cfg['keySensitivity'] if updatedByKeyboard else self._ArcadeCamera__sensitivity
    cfg_MP = cfg * ARCADE_SENS_MP
    eScrollDirection = EScrollDir.convertDZ(dz)
    if eScrollDirection:
        self._ArcadeCamera__overScrollProtector.updateOnScroll(eScrollDirection)
    self._ArcadeCamera__curSenseX = cfg_MP * ARCADE_X_MP
    self._ArcadeCamera__curSenseY = cfg_MP * ARCADE_Y_MP
    self._ArcadeCamera__curScrollSense = self._cfg['keySensitivity'] if updatedByKeyboard else self._ArcadeCamera__scrollSensitivity
    self._ArcadeCamera__updatedByKeyboard = updatedByKeyboard
    if updatedByKeyboard:
        self._ArcadeCamera__autoUpdateDxDyDz.set(dx, dy, dz)
    else:
        self._ArcadeCamera__autoUpdateDxDyDz.set(0)
        self._ArcadeCamera__update(dx, dy, dz, rotateMode, zoomMode)


@overrideIn(ArcadeCamera, condition=isClientWG)
def update(func, self, dx, dy, dz, rotateMode = True, zoomMode = True, updatedByKeyboard = False):
    cfg = self._cfg['keySensitivity'] if updatedByKeyboard else (self._ArcadeCamera__sensitivity * self._userCfg['sensitivity']) if self._ArcadeCamera__sensitivity else self._cfg['sensitivity']
    cfg_MP = cfg * ARCADE_SENS_MP
    eScrollDirection = EScrollDir.convertDZ(dz)
    if eScrollDirection:
        self._ArcadeCamera__overScrollProtector.updateOnScroll(eScrollDirection)
    self._ArcadeCamera__curSenseX = cfg_MP * ARCADE_X_MP
    self._ArcadeCamera__curSenseY = cfg_MP * ARCADE_Y_MP
    self._ArcadeCamera__curScrollSense = self._cfg['keySensitivity'] if updatedByKeyboard else self._ArcadeCamera__scrollSensitivity
    self._ArcadeCamera__updatedByKeyboard = updatedByKeyboard
    if updatedByKeyboard:
        self._ArcadeCamera__autoUpdateDxDyDz.set(dx, dy, dz)
    else:
        self._ArcadeCamera__autoUpdateDxDyDz.set(0)
        self._ArcadeCamera__update(dx, dy, dz, rotateMode, zoomMode)


@overrideIn(ArcadeCamera)
def __updateAngles(func, self, dx, dy):
    yawDelta, pitchDelta = calcYawPitchDelta(self._cfg, self._ArcadeCamera__curSenseX, self._ArcadeCamera__curSenseY, dx, dy)
    self._ArcadeCamera__aimingSystem.handleMovement(yawDelta, -pitchDelta)
    return (self._ArcadeCamera__aimingSystem.yaw, self._ArcadeCamera__aimingSystem.pitch, 0)


@overrideIn(SniperCamera)
def update(func, self, dx, dy, dz, updatedByKeyboard=False):
    cfg = self._cfg['keySensitivity'] if updatedByKeyboard else CameraWithSettings._CameraWithSettings__configs[ArcadeCamera.__name__]['sensitivity']
    cfg_MP = cfg * SNIPER_SENS_MP
    sens_MP = self.__sensitivityMultiplier
    self.__curSenseX = cfg_MP * SNIPER_X_MP
    self.__curSenseY = cfg_MP * SNIPER_Y_MP
    self._SniperCamera__curScrollSense = self._cfg['keySensitivity'] if updatedByKeyboard else self._cfg['scrollSensitivity']
    self.__curSenseX *= sens_MP
    self.__curSenseY *= sens_MP
    if updatedByKeyboard:
        self._SniperCamera__autoUpdateDxDyDz.set(dx, dy, dz)
    else:
        self._SniperCamera__autoUpdateDxDyDz.set(0, 0, 0)
        self._SniperCamera__rotateAndZoom(dx, dy, dz)


@overrideIn(SniperCamera)
def __rotateAndZoom(func, self, dx, dy, dz):
    yawDelta, pitchDelta = calcYawPitchDelta(self._cfg, self.__curSenseX, self.__curSenseY, dx, dy)
    self._SniperCamera__aimingSystem.handleMovement(yawDelta, pitchDelta)
    self._SniperCamera__setupZoom(dz)


@overrideIn(SniperCamera)
def __updateCrosshairMatrix(func, self):
    aspectRatio = BigWorld.getAspectRatio()
    arcadeFov = FovExtended.instance().actualDefaultVerticalFov
    currentFov = BigWorld.projection().fov
    tanCurrentFov = math.tan(currentFov / 2)
    tanSniper = tanCurrentFov * aspectRatio
    tanArcade = math.tan(arcadeFov / 2) * aspectRatio
    self.__sensitivityMultiplier = math.atan(tanSniper) / math.atan(tanArcade)
    curClipPlaneScale = tanCurrentFov
    aimMarkerDistance = self._SniperCamera__aimMarkerDistance * self._DEFAULT_CLIP_PLANE_SCALE / curClipPlaneScale
    self._SniperCamera__crosshairMatrix = createCrosshairMatrix(offsetFromNearPlane=aimMarkerDistance)