'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi
    Copyright (C) 2012-2018 Daniel 'herrnst' Scheller

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import re
import shutil
import time

from xml.etree import ElementTree as xmltree
from array import array

import xbmcvfs
import xbmcgui

from .common import *
from .settings import *
from .extraicons import *
from .infolabels import *
from .charset_hd44780 import *

__lcdxml__        = xbmcvfs.translatePath(os.path.join("special://masterprofile", "LCD.xml"))
__lcddefaultxml__ = xbmcvfs.translatePath(os.path.join(KODI_ADDON_ROOTPATH, "resources", "LCD.xml.defaults"))

class LCD_MODE:
  LCD_MODE_GENERAL     = 0
  LCD_MODE_MUSIC       = 1
  LCD_MODE_VIDEO       = 2
  LCD_MODE_TVSHOW      = 3
  LCD_MODE_NAVIGATION  = 4
  LCD_MODE_SCREENSAVER = 5
  LCD_MODE_XBE_LAUNCH  = 6
  LCD_MODE_PVRTV       = 7
  LCD_MODE_PVRRADIO    = 8
  LCD_MODE_MAX         = 9

class LCD_LINETYPE:
  LCD_LINETYPE_TEXT         = "text"
  LCD_LINETYPE_PROGRESS     = "progressbar"
  LCD_LINETYPE_PROGRESSTIME = "progresstime"
  LCD_LINETYPE_ICONTEXT     = "icontext"
  LCD_LINETYPE_BIGSCREEN    = "bigscreen"

class LCD_LINEALIGN:
  LCD_LINEALIGN_LEFT   = 0
  LCD_LINEALIGN_CENTER = 1
  LCD_LINEALIGN_RIGHT  = 2

g_dictEmptyLineDescriptor = {}
g_dictEmptyLineDescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_TEXT
g_dictEmptyLineDescriptor['startx'] = int(0)
g_dictEmptyLineDescriptor['text'] = str("")
g_dictEmptyLineDescriptor['endx'] = int(0)
g_dictEmptyLineDescriptor['align'] = LCD_LINEALIGN.LCD_LINEALIGN_LEFT

class LcdBase():
  def __init__(self, settings):
    # configuration vars (from LCD.xml)
    self.m_lcdMode = [None] * LCD_MODE.LCD_MODE_MAX
    self.m_extraBars = [None] * (LCD_EXTRABARS_MAX + 1)
    self.m_bAllowEmptyLines = False
    self.m_bCenterBigDigits = False
    self.m_bDisablePlayIndicatorOnPause = False
    self.m_bProgressbarSurroundings = False
    self.m_iDimOnPlayDelay = 0
    self.m_iIconTextOffset = 2
    self.m_strLCDEncoding = "iso-8859-1" # LCDproc default is iso-8859-1!
    self.m_strScrollSeparator = " "

    # runtime vars/state tracking
    self.m_timeDisableOnPlayTimer = time.time()
    self.m_bCurrentlyDimmed = False
    self.m_bHaveHD44780Charmap = False
    self.m_bVolumeChangeActive = False
    self.m_bWasStopped = True
    self.m_bXMLWarningDisplayed = False
    self.m_iOldAudioChannelsVar = 0
    self.m_strOldAudioCodec = ""
    self.m_strOldVideoCodec = ""

    # regex compile cache
    self.m_reBBCode = None

    # class instances
    self.m_Settings = settings

    # initialize InfoLabels
    self.m_InfoLabels = InfoLabels(self.m_Settings)

# @abstractmethod
  def _concrete_method(self):
    pass

# @abstractmethod
  def IsConnected(self):
    pass

# @abstractmethod
  def Stop(self):
    pass

# @abstractmethod
  def Suspend(self):
    pass

# @abstractmethod
  def Resume(self):
    pass

# @abstractmethod
  def SetBackLight(self, iLight):
    pass

# @abstractmethod
  def SetContrast(self, iContrast):
    pass

# @abstractmethod
  def SetBigDigits(self, strTimeString, bForceUpdate):
    pass

# @abstractmethod
  def ClearLine(self, iLine):
    pass

# @abstractmethod
  def SetLine(self, mode, iLine, strLine, dictDescriptor, bForce):
    pass

# @abstractmethod
  def ClearDisplay(self):
    pass

# @abstractmethod
  def FlushLines(self):
    pass

# @abstractmethod
  def GetColumns(self):
    pass

# @abstractmethod
  def GetRows(self):
    pass

# @abstractmethod
  def SetPlayingStateIcon(self):
    pass

# @abstractmethod
  def SetProgressBar(self, percent, lineIdx):
    pass

  def ManageLCDXML(self):
    ret = False

    if not os.path.isfile(__lcdxml__):
      if not os.path.isfile(__lcddefaultxml__):
        log(LOGERROR, "No LCD.xml found and LCD.xml.defaults missing, expect problems!")
      else:
        try:
          shutil.copy2(__lcddefaultxml__, __lcdxml__)
          log(LOGINFO, "Initialised LCD.xml from defaults")
          ret = True
        except:
          log(LOGERROR, "Failed to copy LCD defaults!")
    else:
      ret = True

    return ret

  def Initialize(self):
    bGotDefaultSkin = False
    bSkinHandled = False

    try:
      if not self.m_bHaveHD44780Charmap:
        log(LOGDEBUG, "Registering HD44780-ROM pseudocodepages")
        codecs.register(charset_hd44780)
        self.m_bHaveHD44780Charmap = True
    except:
      log(LOGERROR, "Failed to register custom HD44780-ROM pseudocodepage, expect problems with alternative charsets!")

    # make sure we got reasonable defaults for users who didn't adapt to newest additions
    bGotDefaultSkin = self.LoadSkin(__lcddefaultxml__, True)

    # check for user-LCD.xml, optionally create it
    bSkinHandled = self.ManageLCDXML()

    # try to load user setup
    if not self.LoadSkin(__lcdxml__, False) and not bGotDefaultSkin:
      log(LOGERROR, "No usable mode configuration/skin could be loaded, check your addon installation!")
      return False

    # force-update GUI settings
    self.UpdateGUISettings()

    self.m_bCurrentlyDimmed = False
    return True

  def UpdateGUISettings(self):
    str_charset = self.m_Settings.getCharset()
    if str_charset != self.m_strLCDEncoding:
      if (str_charset == "hd44780_a00" or str_charset == "hd44780_a02") and not self.m_bHaveHD44780Charmap:
        str_charset = "iso8859-1"

      self.m_strLCDEncoding = str_charset
      log(LOGDEBUG, "Setting character encoding to %s" % (self.m_strLCDEncoding))

    self.m_iDimOnPlayDelay = self.m_Settings.getDimDelay()

  def LoadSkin(self, xmlFile, doReset):
    if doReset == True:
      self.Reset()

    bHaveSkin = False

    log(LOGINFO, "Loading settings from %s" % (xmlFile))

    try:
      doc = xmltree.parse(xmlFile)
    except:
      if not self.m_bXMLWarningDisplayed:
        self.m_bXMLWarningDisplayed = True
        text = KODI_ADDON_SETTINGS.getLocalizedString(32502)
        xbmcgui.Dialog().notification(KODI_ADDON_NAME, text, KODI_ADDON_ICON)

      log(LOGERROR, "Parsing of %s failed" % (xmlFile))
      return False

    for element in doc.iter():
      #PARSE LCD infos
      if element.tag == "lcd":
        # load our settings

        # apply scrollseparator
        scrollSeparator = element.find("scrollseparator")
        if scrollSeparator != None:

          if str(scrollSeparator.text).strip() != "":
            self.m_strScrollSeparator = " " + scrollSeparator.text + " "

        # check for progressbarsurroundings setting
        self.m_bProgressbarSurroundings = False

        progressbarSurroundings = element.find("progressbarsurroundings")
        if progressbarSurroundings != None:
          if str(progressbarSurroundings.text).lower() in ["on", "true"]:
            self.m_bProgressbarSurroundings = True

        # apply progressbarblank
        self.m_bProgressbarBlank = " "

        progressbarBlank = element.find("progressbarblank")
        if progressbarBlank != None:
          self.m_bProgressbarBlank = str(progressbarBlank.text)[0]

        # icontext offset setting
        self.m_iIconTextOffset = 2

        icontextoffset = element.find("icontextoffset")
        if icontextoffset != None and icontextoffset.text != None:
          try:
            intoffset = int(icontextoffset.text)
          except ValueError as TypeError:
            log(LOGERROR, "Value for icontextoffset must be integer (got: %s)" % (icontextoffset.text))
          else:
            if intoffset <= 0 or intoffset >= self.GetColumns():
              log(LOGERROR, "Value %d for icontextoffset out of range, ignoring" % (intoffset))
            else:
              if intoffset < 2:
                log(LOGWARNING, "Value %d for icontextoffset smaller than LCDproc's icon width" % (intoffset))
              self.m_iIconTextOffset = intoffset

        # check for allowemptylines setting
        self.m_bAllowEmptyLines = False

        allowemptylines = element.find("allowemptylines")
        if allowemptylines != None:
          if str(allowemptylines.text).lower() in ["on", "true"]:
            self.m_bAllowEmptyLines = True

        # check for centerbigdigits setting
        self.m_bCenterBigDigits = False

        centerbigdigits = element.find("centerbigdigits")
        if centerbigdigits != None:
          if str(centerbigdigits.text).lower() in ["on", "true"]:
            self.m_bCenterBigDigits = True

        # check for disableplayindicatoronpause setting
        self.m_bDisablePlayIndicatorOnPause = False

        disableplayindicatoronpause = element.find("disableplayindicatoronpause")
        if disableplayindicatoronpause != None:
          if str(disableplayindicatoronpause.text).lower() in ["on", "true"]:
            self.m_bDisablePlayIndicatorOnPause = True

        # extra progress bars
        for i in range(1, LCD_EXTRABARS_MAX + 1):
          extrabar = None
          extrabar = element.find("extrabar%i" % (i))
          if extrabar != None:
            if str(extrabar.text).strip() in ["progress", "volume", "volumehidden", "menu", "alwayson"]:
              self.m_extraBars[i] = str(extrabar.text).strip()
            else:
              self.m_extraBars[i] = ""

        #load modes
        tmpMode = element.find("music")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_MUSIC)

        tmpMode = element.find("video")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_VIDEO)

        tmpMode = element.find("tvshow")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_TVSHOW)

        tmpMode = element.find("general")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_GENERAL)

        tmpMode = element.find("navigation")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_NAVIGATION)

        tmpMode = element.find("screensaver")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_SCREENSAVER)

        tmpMode = element.find("xbelaunch")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_XBE_LAUNCH)

        tmpMode = element.find("pvrtv")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_PVRTV)

        tmpMode = element.find("pvrradio")
        self.LoadMode(tmpMode, LCD_MODE.LCD_MODE_PVRRADIO)

        bHaveSkin = True

        # LCD.xml parsed successfully, so reset warning flag
        self.m_bXMLWarningDisplayed = False

    return bHaveSkin

  def LoadMode(self, node, mode):
    # clear mode (probably overriding defaults), assume the user knows what he wants if an empty node is given
    self.m_lcdMode[mode] = []

    if node == None:
      log(LOGWARNING, "Empty Mode %d, consider checking LCD.xml" % (mode))

      # if mode is empty, initialise with blank line
      if len(self.m_lcdMode[mode]) <= 0:
        self.m_lcdMode[mode].append(g_dictEmptyLineDescriptor)

      return

    if len(node.findall("line")) <= 0:
      log(LOGWARNING, "Mode %d defined without lines, consider checking LCD.xml" % (mode))

      if len(self.m_lcdMode[mode]) <= 0:
        self.m_lcdMode[mode].append(g_dictEmptyLineDescriptor)

      return

    # regex to determine any of $INFO[LCD.Time(Wide)21-44]
    timeregex = r'' + re.escape('$INFO[LCD.') + 'Time((Wide)?\d?\d?)' + re.escape(']')

    for line in node.findall("line"):
      # initialize line with empty descriptor
      linedescriptor = g_dictEmptyLineDescriptor.copy()

      linedescriptor['startx'] = int(1)
      linedescriptor['endx'] = int(self.GetColumns())

      if line.text == None:
        linetext = ""
      else:
        # prepare text line for XBMC's expected encoding
        linetext = line.text.strip()

      # make sure linetext has something so re.match won't fail
      if linetext != "":
        timematch = re.match(timeregex, linetext, flags=re.IGNORECASE)

        # if line matches, throw away mode, add BigDigit descriptor and end processing for this mode
        if timematch != None:
          linedescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_BIGSCREEN
          linedescriptor['text'] = "Time"

          self.m_lcdMode[mode] = []
          self.m_lcdMode[mode].append(linedescriptor)
          return

      # progressbar line if InfoLabel exists
      if linetext.lower().find("$info[lcd.progressbar]") >= 0:
        linedescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_PROGRESS
        linedescriptor['text'] = self.m_bProgressbarBlank * int(self.m_iColumns)
        linedescriptor['endx'] = int(self.m_iCellWidth) * int(self.m_iColumns)

        if self.m_bProgressbarSurroundings == True:
          linedescriptor['startx'] = int(2)
          linedescriptor['text'] = "[" + self.m_bProgressbarBlank * (self.m_iColumns - 2) + "]"
          linedescriptor['endx'] = int(self.m_iCellWidth) * (int(self.GetColumns()) - 2)

      # progresstime line if InfoLabel exists
      elif linetext.lower().find("$info[lcd.progresstime]") >= 0:
        linedescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_PROGRESSTIME
        linedescriptor['endx'] = int(self.m_iCellWidth) * int(self.m_iColumns)

      # textline with icon in front
      elif linetext.lower().find("$info[lcd.playicon]") >= 0:
        linedescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_ICONTEXT
        linedescriptor['startx'] = int(1 + self.m_iIconTextOffset) # icon widgets take 2 chars, so shift text offset (default: 2)
        linedescriptor['text'] = re.sub(r'\s?' + re.escape("$INFO[LCD.PlayIcon]") + '\s?', ' ', linetext, flags=re.IGNORECASE).strip()

      # standard (scrolling) text line
      else:
        linedescriptor['type'] = LCD_LINETYPE.LCD_LINETYPE_TEXT
        linedescriptor['text'] = linetext

      # check for alignment pseudo-labels
      if linetext.lower().find("$info[lcd.aligncenter]") >= 0:
        linedescriptor['align'] = LCD_LINEALIGN.LCD_LINEALIGN_CENTER
      if linetext.lower().find("$info[lcd.alignright]") >= 0:
        linedescriptor['align'] = LCD_LINEALIGN.LCD_LINEALIGN_RIGHT

      linedescriptor['text'] = re.sub(r'\s?' + re.escape("$INFO[LCD.AlignCenter]") + '\s?', ' ', linedescriptor['text'], flags=re.IGNORECASE).strip()
      linedescriptor['text'] = re.sub(r'\s?' + re.escape("$INFO[LCD.AlignRight]") + '\s?', ' ', linedescriptor['text'], flags=re.IGNORECASE).strip()

      self.m_lcdMode[mode].append(linedescriptor)

  def Reset(self):
    for i in range(0,LCD_MODE.LCD_MODE_MAX):
      self.m_lcdMode[i] = []			#clear list

  def Shutdown(self):
    log(LOGINFO, "Shutting down")

    if self.m_Settings.getDimOnShutdown():
      self.SetBackLight(0)

    self.CloseSocket()

  # GetLCDMode():
  # returns mode identifier based on currently playing media/active navigation
  def GetLCDMode(self):
    ret = LCD_MODE.LCD_MODE_GENERAL

    navActive = self.m_InfoLabels.IsNavigationActive()
    screenSaver = self.m_InfoLabels.IsScreenSaverActive()
    playingVideo = self.m_InfoLabels.PlayingVideo()
    playingTVShow = self.m_InfoLabels.PlayingTVShow()
    playingMusic = self.m_InfoLabels.PlayingAudio()
    playingPVRTV = self.m_InfoLabels.PlayingLiveTV()
    playingPVRRadio = self.m_InfoLabels.PlayingLiveRadio()

    if navActive:
      ret = LCD_MODE.LCD_MODE_NAVIGATION
    elif screenSaver:
      ret = LCD_MODE.LCD_MODE_SCREENSAVER
    elif playingPVRTV:
      ret = LCD_MODE.LCD_MODE_PVRTV
    elif playingPVRRadio:
      ret = LCD_MODE.LCD_MODE_PVRRADIO
    elif playingTVShow:
      ret = LCD_MODE.LCD_MODE_TVSHOW
    elif playingVideo:
      ret = LCD_MODE.LCD_MODE_VIDEO
    elif playingMusic:
      ret = LCD_MODE.LCD_MODE_MUSIC

    return ret

  def StripBBCode(self, strtext):
    regexbbcode = "\[(?P<tagname>[0-9a-zA-Z_\-]+?)[0-9a-zA-Z_\- ]*?\](?P<content>.*?)\[\/(?P=tagname)\]"
    # precompile and remember regex to make sure re's caching won't cause accidential recompilation
    if not self.m_reBBCode:
      self.m_reBBCode = re.compile(regexbbcode)
      # catch+report failure
      if not self.m_reBBCode:
        log(LOGWARNING, "Precompilation of BBCode strip regex failed")
        self.m_reBBCode = regexbbcode

    # loop to catch nested tags
    loopcount = 5

    # start with passed string
    mangledline = strtext

    # do regex multiple times to catch nested tags
    while True:
      loopcount = loopcount - 1
      try:
        mangledline, replacements = re.subn(self.m_reBBCode, "\g<content>", mangledline)
      except:
        return mangledline

      # when the result didn't change, all tags should be gone (but also stop if maxnum iterations are reached)
      if replacements == 0 or loopcount < 1:
        break

    # return last replace mangling
    return mangledline

  def Render(self, bForce):
    outLine = 0
    inLine = 0
    mode = self.GetLCDMode()

    self.HandleBacklight(mode)

    while (outLine < int(self.GetRows()) and inLine < len(self.m_lcdMode[mode])):
      #parse the progressbar infolabel by ourselfs!
      if self.m_lcdMode[mode][inLine]['type'] == LCD_LINETYPE.LCD_LINETYPE_PROGRESS or self.m_lcdMode[mode][inLine]['type'] == LCD_LINETYPE.LCD_LINETYPE_PROGRESSTIME:
        # get playtime and duration and convert into seconds
        percent = self.m_InfoLabels.GetProgressPercent()
        pixelsWidth = self.SetProgressBar(percent, self.m_lcdMode[mode][inLine]['endx'])
        line = "p" + str(pixelsWidth)
      else:
        if self.m_lcdMode[mode][inLine]['type'] == LCD_LINETYPE.LCD_LINETYPE_ICONTEXT:
          self.SetPlayingStateIcon()

        line = self.m_InfoLabels.GetInfoLabel(self.m_lcdMode[mode][inLine]['text'])

        if len(line) > 0:
          line = self.StripBBCode(line)

        self.SetProgressBar(0, -1)

      if self.m_bAllowEmptyLines or len(line) > 0:
        self.SetLine(mode, outLine, line, self.m_lcdMode[mode][inLine], bForce)
        outLine += 1

      inLine += 1

    # fill remainder with empty space if not bigscreen
    if self.m_lcdMode[mode][0]['type'] != LCD_LINETYPE.LCD_LINETYPE_BIGSCREEN:
      while outLine < int(self.GetRows()):
        self.SetLine(mode, outLine, "", g_dictEmptyLineDescriptor, bForce)
        outLine += 1

    if self.m_cExtraIcons is not None:
      self.SetExtraInformation()
      self.m_bstrSetLineCmds += self.m_cExtraIcons.GetOutputCommands()

    self.FlushLines()

  def DoDimOnMusic(self, mode):
    return (mode == LCD_MODE.LCD_MODE_MUSIC or mode == LCD_MODE.LCD_MODE_PVRRADIO) and self.m_Settings.getDimOnMusicPlayback()

  def DoDimOnVideo(self, mode):
    return (mode == LCD_MODE.LCD_MODE_VIDEO or mode == LCD_MODE.LCD_MODE_TVSHOW or mode == LCD_MODE.LCD_MODE_PVRTV) and self.m_Settings.getDimOnVideoPlayback()

  def DoDimOnScreensaver(self, mode):
    return (mode == LCD_MODE.LCD_MODE_SCREENSAVER) and self.m_Settings.getDimOnScreensaver()

  def HandleBacklight(self, mode):
    # dimming display in case screensaver is active or something is being played back (and not paused!)
    doDim = False

    if self.DoDimOnScreensaver(mode):
      doDim = True
    elif not (self.m_InfoLabels.IsPlayerPlaying() and self.m_InfoLabels.IsPlayerPaused()) and (self.DoDimOnVideo(mode) or self.DoDimOnMusic(mode)):
      doDim = True

    if doDim:
      if not self.m_bCurrentlyDimmed:
        if (self.m_timeDisableOnPlayTimer + self.m_iDimOnPlayDelay) < time.time():
          self.SetBackLight(0)
          self.m_bCurrentlyDimmed = True
    else:
      self.m_timeDisableOnPlayTimer = time.time()
      if self.m_bCurrentlyDimmed:
        self.SetBackLight(1)
        self.m_bCurrentlyDimmed = False

  def SetExtraInfoPlaying(self, isplaying, isvideo, isaudio):
    # make sure output scaling indicators are off when not playing and/or not playing video
    if not isplaying or not isvideo:
      self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_OUTSCALE)

    if isplaying:
      if isvideo:
        try:
          iVideoRes = int(self.m_InfoLabels.GetInfoLabel("VideoPlayer.VideoResolution"))
        except:
          iVideoRes = int(0)

        try:
          iScreenRes = int(self.m_InfoLabels.GetInfoLabel("System.ScreenHeight"))
        except:
          iScreenRes = int(0)

        if self.m_InfoLabels.PlayingLiveTV():
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_TV, True)
        elif self.m_InfoLabels.IsInternetStream():
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_WEBCASTING, True)
        else:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MOVIE, True)

        if iVideoRes < 720:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_RESOLUTION_SD, True)
        else:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_RESOLUTION_HD, True)

        if iScreenRes <= (iVideoRes + (float(iVideoRes) * 0.1)) and iScreenRes >= (iVideoRes - (float(iVideoRes) * 0.1)):
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_OUTSOURCE, True)
        else:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_OUTFIT, True)

      elif isaudio:
        if self.m_InfoLabels.IsInternetStream():
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_WEBCASTING, True)
        else:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MUSIC, True)

    else: # not playing

      # Set active mode indicator based on current active window
      iWindowID = self.m_InfoLabels.GetActiveWindowID()

      if self.m_InfoLabels.IsWindowIDPVR(iWindowID):
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_TV, True)
      elif self.m_InfoLabels.IsWindowIDVideo(iWindowID):
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MOVIE, True)
      elif self.m_InfoLabels.IsWindowIDMusic(iWindowID):
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MUSIC, True)
      elif self.m_InfoLabels.IsWindowIDPictures(iWindowID):
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_PHOTO, True)
      elif self.m_InfoLabels.IsWindowIDWeather(iWindowID):
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_WEATHER, True)
      else:
        self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_MODES)

  def SetExtraInfoCodecs(self, isplaying, isvideo, isaudio):
    # initialise stuff to avoid uninitialised var stuff
    strVideoCodec = ""
    strAudioCodec = ""
    iAudioChannels = 0

    if isplaying:
      if self.m_InfoLabels.IsPassthroughAudio():
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_SPDIF, True)
      else:
        self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_SPDIF, False)

      if isvideo:
        strVideoCodec = str(self.m_InfoLabels.GetInfoLabel("VideoPlayer.VideoCodec")).lower()
        strAudioCodec = str(self.m_InfoLabels.GetInfoLabel("VideoPlayer.AudioCodec")).lower()
        iAudioChannels = self.m_InfoLabels.GetInfoLabel("VideoPlayer.AudioChannels")
      elif isaudio:
        strVideoCodec = ""
        strAudioCodec = str(self.m_InfoLabels.GetInfoLabel("MusicPlayer.Codec")).lower()
        iAudioChannels = self.m_InfoLabels.GetInfoLabel("MusicPlayer.Channels")

      if self.m_bWasStopped:
        self.m_bWasStopped = False
        self.m_strOldVideoCodec = ""
        self.m_strOldAudioCodec = ""
        self.m_iOldAudioChannelsVar = 0

      # check video codec
      if self.m_strOldVideoCodec != strVideoCodec:
        # work only when video codec changed
        self.m_strOldVideoCodec = strVideoCodec

        # any mpeg video
        # FIXME: "hdmv" is returned as video codec for ANYTHING played directly
        # from bluray media played via libbluray and friends, regardless of the
        # real codec (mpeg2/h264/vc1). Ripping to e.g. MKV and playing that back
        # returns the correct codec id. As the display is wrong for VC-1 only,
        # accept that the codec icon is right only in maybe 70-80% of all playback
        # cases. This needs fixing in XBMC! See http://trac.xbmc.org/ticket/13969
        if strVideoCodec in ["mpg", "mpeg", "mpeg2video", "h264", "x264", "mpeg4", "hdmv", "hevc"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_MPEG, True)

        # any divx
        elif strVideoCodec in ["divx", "dx50", "div3"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_DIVX, True)

        # xvid
        elif strVideoCodec == "xvid":
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_XVID, True)

        # wmv and vc-1
        elif strVideoCodec in ["wmv", "wvc1", "vc-1", "vc1"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_WMV, True)

        # anything else
        else:
          self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_VIDEOCODECS)

      # check audio codec
      if self.m_strOldAudioCodec != strAudioCodec:
        # work only when audio codec changed
        self.m_strOldAudioCodec = strAudioCodec

        # any mpeg audio
        if strAudioCodec in ["mpga", "mp2"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_MPEG, True)

        # any ac3/dolby digital/dd+/truehd
        elif strAudioCodec in ["ac3", "eac3", "truehd"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_AC3, True)

        # any dts including hires variants
        elif strAudioCodec in ["dts", "dca", "dtshd_hra", "dtshd_ma"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_DTS, True)

        # mp3
        elif strAudioCodec in ["mp3", "mp3float"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_MP3, True)

        # any ogg vorbis
        elif strAudioCodec in ["ogg", "vorbis"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_OGG, True)

        # any wma
        elif strAudioCodec in ["wma", "wmav2"]:
          if isvideo:
            self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_VWMA, True)
          else:
            self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_AWMA, True)

        # any pcm, wav or flac
        elif strAudioCodec in ["wav", "flac", "pcm", "pcm_bluray", "pcm_s24le"]:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_WAV, True)

        # anything else
        else:
          self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_AUDIOCODECS)

      # make sure iAudioChannels contains something useful
      if iAudioChannels == "" and strAudioCodec != "":
        iAudioChannels = 2
      elif iAudioChannels == "":
        iAudioChannels = 0
      else:
        iAudioChannels = int(iAudioChannels)

      # update audio channels indicator
      if self.m_iOldAudioChannelsVar != iAudioChannels:
        # work only when audio channels changed
        self.m_iOldAudioChannelsVar = iAudioChannels

        # decide which icon (set) to activate
        if iAudioChannels > 0 and iAudioChannels <= 3:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_OUT_2_0, True)
        elif iAudioChannels <= 6:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_OUT_5_1, True)
        elif iAudioChannels <= 8:
          self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_OUT_7_1, True)
        else:
          self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_AUDIOCHANNELS)

    else:
      self.m_cExtraIcons.ClearIconStates(LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_CODECS)
      self.m_bWasStopped = True

  def SetExtraInfoGeneric(self, ispaused):
    if self.m_InfoLabels.IsMuted():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MUTE, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_MUTE, False)

    if ispaused:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_PAUSE, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_PAUSE, False)

    if self.m_InfoLabels.IsPVRRecording():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_RECORD, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_RECORD, False)

    if self.m_InfoLabels.IsPlaylistRandom():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_SHUFFLE, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_SHUFFLE, False)

    if self.m_InfoLabels.IsPlaylistRepeatAny():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_REPEAT, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_REPEAT, False)

    if self.m_InfoLabels.IsDiscInDrive():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_DISC_IN, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_DISC_IN, False)

    if self.m_InfoLabels.IsScreenSaverActive():
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_TIME, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_TIME, False)

    if self.m_InfoLabels.WindowIsActive(WINDOW_IDS.WINDOW_DIALOG_VOLUME_BAR):
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VOLUME, True)
      self.m_bVolumeChangeActive = True
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_VOLUME, False)
      self.m_bVolumeChangeActive = False

    if self.m_InfoLabels.WindowIsActive(WINDOW_IDS.WINDOW_DIALOG_KAI_TOAST):
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ALARM, True)
    else:
      self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_ALARM, False)

  def SetExtraInfoBars(self, isplaying):
    for i in range(1, LCD_EXTRABARS_MAX + 1):
      if self.m_extraBars[i] == "progress":
        if isplaying:
          self.m_cExtraIcons.SetBar(i, (self.m_InfoLabels.GetProgressPercent() * 100))
        else:
          self.m_cExtraIcons.SetBar(i, 0)
      elif self.m_extraBars[i] == "volume":
        self.m_cExtraIcons.SetBar(i, self.m_InfoLabels.GetVolumePercent())
      elif self.m_extraBars[i] == "volumehidden":
        if self.m_bVolumeChangeActive:
          self.m_cExtraIcons.SetBar(i, self.m_InfoLabels.GetVolumePercent())
        else:
          self.m_cExtraIcons.SetBar(i, 0)
      elif self.m_extraBars[i] == "menu":
        if isplaying:
          self.m_cExtraIcons.SetBar(i, 0)
        else:
          self.m_cExtraIcons.SetBar(i, 100)
      elif self.m_extraBars[i] == "alwayson":
        self.m_cExtraIcons.SetBar(i, 100)
      else:
        self.m_cExtraIcons.SetBar(i, 0)

  def SetExtraInformation(self):
    bPaused = self.m_InfoLabels.IsPlayerPaused()
    bPlaying = self.m_InfoLabels.IsPlayerPlaying()

    bIsVideo = self.m_InfoLabels.PlayingVideo()
    bIsAudio = self.m_InfoLabels.PlayingAudio()

    self.m_cExtraIcons.SetIconState(LCD_EXTRAICONS.LCD_EXTRAICON_PLAYING,
      bPlaying and not (bPaused and self.m_bDisablePlayIndicatorOnPause))

    self.SetExtraInfoPlaying(bPlaying, bIsVideo, bIsAudio)
    self.SetExtraInfoCodecs(bPlaying, bIsVideo, bIsAudio)
    self.SetExtraInfoGeneric(bPaused)
    self.SetExtraInfoBars(bPlaying)
