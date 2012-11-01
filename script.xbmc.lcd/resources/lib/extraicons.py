'''
    XBMC LCDproc addon
    Copyright (C) 2012 Team XBMC
    
    Extra icon defines/enums
    Copyright (C) 2012 Daniel Scheller
    
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

# enum snippet from http://stackoverflow.com/a/1695250 - thanks!
def enum(*sequential, **named):
  enums = dict(zip(sequential, range(len(sequential))), **named)
  return type('Enum', (), enums)

LCD_EXTRABARS_MAX = 4

LCD_EXTRAICONS = enum(
  'LCD_EXTRAICON_NONE',
  'LCD_EXTRAICON_PLAYING',
  'LCD_EXTRAICON_PAUSE',
  'LCD_EXTRAICON_MOVIE',
  'LCD_EXTRAICON_MUSIC',
  'LCD_EXTRAICON_WEATHER',
  'LCD_EXTRAICON_TV',
  'LCD_EXTRAICON_PHOTO',
  'LCD_EXTRAICON_MUTE',
  'LCD_EXTRAICON_REPEAT',
  'LCD_EXTRAICON_SHUFFLE',
  'LCD_EXTRAICON_ALARM',
  'LCD_EXTRAICON_RECORD',
  'LCD_EXTRAICON_VOLUME',
  'LCD_EXTRAICON_TIME',
  'LCD_EXTRAICON_SPDIF',
  'LCD_EXTRAICON_DISC_IN',
  'LCD_EXTRAICON_SCR1',
  'LCD_EXTRAICON_SCR2',
  'LCD_EXTRAICON_RESOLUTION_SD',
  'LCD_EXTRAICON_RESOLUTION_HD',
  'LCD_EXTRAICON_VCODEC_MPEG',
  'LCD_EXTRAICON_VCODEC_DIVX',
  'LCD_EXTRAICON_VCODEC_XVID',
  'LCD_EXTRAICON_VCODEC_WMV',
  'LCD_EXTRAICON_ACODEC_MPEG',
  'LCD_EXTRAICON_ACODEC_AC3',
  'LCD_EXTRAICON_ACODEC_DTS',
  'LCD_EXTRAICON_ACODEC_VWMA', # e.g. iMON has video-WMA AND audio-WMA...
  'LCD_EXTRAICON_ACODEC_MP3',
  'LCD_EXTRAICON_ACODEC_OGG',
  'LCD_EXTRAICON_ACODEC_AWMA', # see ACODEC_VWMA
  'LCD_EXTRAICON_ACODEC_WAV',
  'LCD_EXTRAICON_OUTSOURCE',
  'LCD_EXTRAICON_OUTFIT',
  'LCD_EXTRAICON_OUT_2_0',
  'LCD_EXTRAICON_OUT_5_1',
  'LCD_EXTRAICON_OUT_7_1',
  'LCD_EXTRAICON_MAX'
)

LCD_EXTRAICONCATEGORIES = enum(
  'LCD_ICONCAT_MODES',
  'LCD_ICONCAT_CODECS',
  'LCD_ICONCAT_VIDEOCODECS',
  'LCD_ICONCAT_AUDIOCODECS',
  'LCD_ICONCAT_AUDIOCHANNELS'
)

'''
class LCD_EXTRAICONS_CLASS:
  LCD_EXTRAICON_BLANK = 0
  LCD_EXTRAICON_PLAYING = 1
  LCD_EXTRAICON_PAUSE = 2
  LCD_EXTRAICON_MOVIE = 3
  LCD_EXTRAICON_MUSIC = 4
  LCD_EXTRAICON_WEATHER = 5
  LCD_EXTRAICON_TV = 6
  LCD_EXTRAICON_PHOTO = 7
  LCD_EXTRAICON_RESOLUTION_SD = 8
  LCD_EXTRAICON_RESOLUTION_HD = 9
  LCD_EXTRAICON_MUTE = 10
  LCD_EXTRAICON_REPEAT = 11
  LCD_EXTRAICON_SHUFFLE = 12
  LCD_EXTRAICON_ALARM = 13
  LCD_EXTRAICON_RECORD = 14
  LCD_EXTRAICON_VOLUME = 15
  LCD_EXTRAICON_TIME = 16
  LCD_EXTRAICON_SPDIF = 17
  LCD_EXTRAICON_DISC_IN = 18
  LCD_EXTRAICON_OUTSOURCE = 19
  LCD_EXTRAICON_OUTFIT = 20
  LCD_EXTRAICON_SCR1 = 21
  LCD_EXTRAICON_SCR2 = 22
  LCD_EXTRAICON_VCODEC_MPEG = 23
  LCD_EXTRAICON_VCODEC_DIVX = 24
  LCD_EXTRAICON_VCODEC_XVID = 25
  LCD_EXTRAICON_VCODEC_WMV = 26
  LCD_EXTRAICON_ACODEC_MPEG = 27
  LCD_EXTRAICON_ACODEC_AC3 = 28
  LCD_EXTRAICON_ACODEC_DTS = 29
  LCD_EXTRAICON_ACODEC_VWMA = 30 # e.g. iMON has video-WMA AND audio-WMA...
  LCD_EXTRAICON_ACODEC_MP3 = 31
  LCD_EXTRAICON_ACODEC_OGG = 32
  LCD_EXTRAICON_ACODEC_AWMA = 33 # see ACODEC_VWMA
  LCD_EXTRAICON_ACODEC_WAV = 34
  LCD_EXTRAICON_OUT_2_0 = 35
  LCD_EXTRAICON_OUT_5_1 = 36
  LCD_EXTRAICON_OUT_7_1 = 37
'''
