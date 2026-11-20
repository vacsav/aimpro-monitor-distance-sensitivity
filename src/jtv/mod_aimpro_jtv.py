import os, json, copy, math, BigWorld
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


def overrideIn(cls, condition = lambda: True):

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


MOD_NAME = 'mod_aimpro_jtv'
CONFIG_NAME = 'jtv'
METHOD_KEY = CONFIG_NAME.upper()
METHOD_DEFAULT = 100.0 if CONFIG_NAME in ('jth', 'jtv') else 0.0

CONFIG_VERSION = 2

DEFAULT_CONFIG = {
    "ConfigVersion": CONFIG_VERSION,
    "Arcade": {
        "Y_Multiplier": "1.0",
        "X_Multiplier": "1.0",
        "Sensitivity_Multiplier": "1.0"
    },
    "Sniper": {
        METHOD_KEY: str(METHOD_DEFAULT),
        "Y_Multiplier": "1.0",
        "X_Multiplier": "1.0",
        "Sensitivity_Multiplier": "1.0",
        "Sensitivity_Multiplier_x1": "1.0"
    }
}

CONFIG_PATH = os.path.join('mods', 'configs', 'AimPro', CONFIG_NAME + '.json')
CONFIG_DIR = os.path.dirname(CONFIG_PATH)

def writeDefaultConfig():
    try:
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print('[%s] %s.json created' % (MOD_NAME, CONFIG_NAME))
        return True
    except Exception as e:
        print('[%s] Failed to write %s.json: %r' % (MOD_NAME, CONFIG_NAME, e))
        return False

def ensureConfigExists():
    if not os.path.isfile(CONFIG_PATH):
        writeDefaultConfig()
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print('[%s] Failed to read %s (%r), recreating' % (MOD_NAME, CONFIG_PATH, e))
        writeDefaultConfig()
        return copy.deepcopy(DEFAULT_CONFIG)
    rawVersion = data.get("ConfigVersion")
    if isinstance(rawVersion, bool) or not isinstance(rawVersion, int):
        fileVersion = None
    else:
        fileVersion = rawVersion
    if fileVersion != CONFIG_VERSION:
        print('[%s] Config version mismatch (%r -> %d), recreating' % (MOD_NAME, rawVersion, CONFIG_VERSION))
        writeDefaultConfig()
        return copy.deepcopy(DEFAULT_CONFIG)
    return data

def loadConfig():
    return ensureConfigExists()

CONFIG = loadConfig()

def safeFloat(value, default=1.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        print('[%s] Invalid float value %r, using %r' % (MOD_NAME, value, default))
        return default

ARCADE_CFG = CONFIG.get('Arcade', {})
ARCADE_Y_MP  = safeFloat(ARCADE_CFG.get('Y_Multiplier', 1.0))
ARCADE_X_MP  = safeFloat(ARCADE_CFG.get('X_Multiplier', 1.0))
ARCADE_SENS_MP = safeFloat(ARCADE_CFG.get('Sensitivity_Multiplier', 1.0))
ARCADE_TOTAL_X_MP = (ARCADE_SENS_MP * ARCADE_X_MP)
ARCADE_TOTAL_Y_MP = (ARCADE_SENS_MP * ARCADE_Y_MP)

SNIPER_CFG = CONFIG.get('Sniper', {})
SNIPER_METHOD_VALUE = safeFloat(SNIPER_CFG.get(METHOD_KEY), METHOD_DEFAULT)
SNIPER_Y_MP  = safeFloat(SNIPER_CFG.get('Y_Multiplier', 1.0))
SNIPER_X_MP  = safeFloat(SNIPER_CFG.get('X_Multiplier', 1.0))
SNIPER_SENS_MP = safeFloat(SNIPER_CFG.get('Sensitivity_Multiplier', 1.0))
SNIPER_SENS_MP_X1 = float(SNIPER_CFG.get('Sensitivity_Multiplier_x1', 1.0))
SNIPER_TOTAL_X_MP = (SNIPER_SENS_MP * SNIPER_X_MP)
SNIPER_TOTAL_Y_MP = (SNIPER_SENS_MP * SNIPER_Y_MP)


VANILLA_ARCADE_CFG = None
def getArcadeSensitivity():
    global VANILLA_ARCADE_CFG
    if VANILLA_ARCADE_CFG is None:
        VANILLA_ARCADE_CFG = CameraWithSettings._CameraWithSettings__configs.get('ArcadeCamera')
    return VANILLA_ARCADE_CFG['sensitivity'] if VANILLA_ARCADE_CFG else 1.0


CACHED_JEDI_DATA = None
LAST_KNOWN_ARCADE_FOV = None
def getJediVerticalData():
    global CACHED_JEDI_DATA, LAST_KNOWN_ARCADE_FOV
    arcadeFov = FovExtended.instance().actualDefaultVerticalFov
    if (CACHED_JEDI_DATA is not None and arcadeFov == LAST_KNOWN_ARCADE_FOV):
        return CACHED_JEDI_DATA
    LAST_KNOWN_ARCADE_FOV = arcadeFov
    tanArcadeFov = math.tan(arcadeFov * 0.5)
    jedi = SNIPER_METHOD_VALUE / 100.0
    if jedi == 0.0:
        CACHED_JEDI_DATA = (0, tanArcadeFov, None, None)
        return CACHED_JEDI_DATA
    if jedi > 0:
        mode = 1
        jediAbs = jedi
    else:
        mode = 2
        jediAbs = -jedi
    atanJediAbsTanArcade = math.atan(jediAbs * tanArcadeFov)
    CACHED_JEDI_DATA = (mode, tanArcadeFov, jediAbs, atanJediAbsTanArcade)
    return CACHED_JEDI_DATA


def modCalcYawPitchDelta(cfg, curSenseX, curSenseY, dx, dy):
    return (dx * curSenseX * (-1 if cfg['horzInvert'] else 1), dy * curSenseY * (-1 if cfg['vertInvert'] else 1))
AvatarInputHandler.DynamicCameras.calcYawPitchDelta = modCalcYawPitchDelta
calcYawPitchDelta = AvatarInputHandler.DynamicCameras.calcYawPitchDelta


origArcadeInit = ArcadeCamera.__init__
def modArcadeInit(self, *args, **kwargs):
    origArcadeInit(self, *args, **kwargs)
    self._ArcadeCamera__curSenseX = 0
    self._ArcadeCamera__curSenseY = 0
ArcadeCamera.__init__ = modArcadeInit


origSniperInit = SniperCamera.__init__
def modSniperInit(self, *args, **kwargs):
    origSniperInit(self, *args, **kwargs)
    self._SniperCamera__curSenseX = 0
    self._SniperCamera__curSenseY = 0
    self._SniperCamera__sensitivityMultiplier = 1.0
SniperCamera.__init__ = modSniperInit


@overrideIn(ArcadeCamera, condition = isClientLesta)
def update(func, self, dx, dy, dz, rotateMode = True, zoomMode = True, updatedByKeyboard = False):
    eScrollDirection = EScrollDir.convertDZ(dz)
    if eScrollDirection:
        self._ArcadeCamera__overScrollProtector.updateOnScroll(eScrollDirection)
    if updatedByKeyboard:
        cfg = self._cfg['keySensitivity']
        scroll = cfg
    else:
        cfg = self._ArcadeCamera__sensitivity
        scroll = self._ArcadeCamera__scrollSensitivity
    self._ArcadeCamera__curSenseX = (ARCADE_TOTAL_X_MP * cfg)
    self._ArcadeCamera__curSenseY = (ARCADE_TOTAL_Y_MP * cfg)
    self._ArcadeCamera__curScrollSense = scroll
    self._ArcadeCamera__updatedByKeyboard = updatedByKeyboard
    if not updatedByKeyboard:
        self._ArcadeCamera__autoUpdateDxDyDz.set(0)
        self._ArcadeCamera__update(dx, dy, dz, rotateMode, zoomMode)
        return
    self._ArcadeCamera__autoUpdateDxDyDz.set(dx, dy, dz)


@overrideIn(ArcadeCamera, condition = isClientWG)
def update(func, self, dx, dy, dz, rotateMode=True, zoomMode=True, updatedByKeyboard=False):
    eScrollDirection = EScrollDir.convertDZ(dz)
    if eScrollDirection:
        self._ArcadeCamera__overScrollProtector.updateOnScroll(eScrollDirection)
    cfgData = self._cfg
    if updatedByKeyboard:
        cfg = cfgData['keySensitivity']
        scroll = cfg
    elif self._ArcadeCamera__sensitivity:
        cfg = self._ArcadeCamera__sensitivity * self._userCfg['sensitivity']
        scroll = self._ArcadeCamera__scrollSensitivity
    else:
        cfg = cfgData['sensitivity']
        scroll = self._ArcadeCamera__scrollSensitivity
    self._ArcadeCamera__curSenseX = ARCADE_TOTAL_X_MP * cfg
    self._ArcadeCamera__curSenseY = ARCADE_TOTAL_Y_MP * cfg
    self._ArcadeCamera__curScrollSense = scroll
    self._ArcadeCamera__updatedByKeyboard = updatedByKeyboard
    if not updatedByKeyboard:
        self._ArcadeCamera__autoUpdateDxDyDz.set(0)
        self._ArcadeCamera__update(dx, dy, dz, rotateMode, zoomMode)
        return
    self._ArcadeCamera__autoUpdateDxDyDz.set(dx, dy, dz)


@overrideIn(ArcadeCamera)
def __updateAngles(func, self, dx, dy):
    yawDelta, pitchDelta = calcYawPitchDelta(self._cfg, self._ArcadeCamera__curSenseX, self._ArcadeCamera__curSenseY, dx, dy)
    self._ArcadeCamera__aimingSystem.handleMovement(yawDelta, -pitchDelta)
    return (self._ArcadeCamera__aimingSystem.yaw, self._ArcadeCamera__aimingSystem.pitch, 0)


@overrideIn(SniperCamera)
def update(func, self, dx, dy, dz, updatedByKeyboard=False):
    cfgData = self._cfg
    if updatedByKeyboard:
        cfg = cfgData['keySensitivity']
        scroll = cfg
    else:
        cfg = getArcadeSensitivity()
        scroll = cfgData['scrollSensitivity']
    finalSensitivity = (cfg * self._SniperCamera__sensitivityMultiplier)
    self._SniperCamera__curSenseX = (SNIPER_TOTAL_X_MP * finalSensitivity)
    self._SniperCamera__curSenseY = (SNIPER_TOTAL_Y_MP * finalSensitivity)
    self._SniperCamera__curScrollSense = scroll
    if not updatedByKeyboard:
        self._SniperCamera__autoUpdateDxDyDz.set(0, 0, 0)
        self._SniperCamera__rotateAndZoom(dx, dy, dz)
        return
    self._SniperCamera__autoUpdateDxDyDz.set(dx, dy, dz)


@overrideIn(SniperCamera)
def __rotateAndZoom(func, self, dx, dy, dz):
    yawDelta, pitchDelta = calcYawPitchDelta(self._cfg, self._SniperCamera__curSenseX, self._SniperCamera__curSenseY, dx, dy)
    self._SniperCamera__aimingSystem.handleMovement(yawDelta, pitchDelta)
    self._SniperCamera__setupZoom(dz)


@overrideIn(SniperCamera)
def __updateCrosshairMatrix(func, self):
    currentFov = BigWorld.projection().fov
    tanCurrentFov = math.tan(currentFov * 0.5)
    aimMarkerDistance = (self._SniperCamera__aimMarkerDistance * self._DEFAULT_CLIP_PLANE_SCALE / tanCurrentFov)
    self._SniperCamera__crosshairMatrix = createCrosshairMatrix(offsetFromNearPlane=aimMarkerDistance)

    mode, tanArcadeFov, jediAbs, atanJediAbsTanArcade = getJediVerticalData()
    F = tanArcadeFov / tanCurrentFov
    if mode == 0:
        multiplier = 1.0 / F
    elif mode == 1:
        J = atanJediAbsTanArcade / math.atan(jediAbs * tanCurrentFov)
        FJ_avg = (F + J) * 0.5
        multiplier = 1.0 / FJ_avg
    else:
        J = 1.0 / (2.0 * tanCurrentFov / tanArcadeFov - math.atan(jediAbs * tanCurrentFov) / atanJediAbsTanArcade)
        FJ_avg = (F + J) * 0.5
        multiplier = 1.0 / FJ_avg
    if self._SniperCamera__zoom == 1.0:
        multiplier *= SNIPER_SENS_MP_X1
    self._SniperCamera__sensitivityMultiplier = multiplier