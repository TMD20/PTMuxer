
from pickle import GET
import re
import time
import datetime as dt

import xxhash
import langcodes
import arrow

import tools.general as utils


class TracksData():
    def __init__(self):
        self._rawMediaTracksData = {}
        self._sources = []

    """
    Public Functions
    """

    ################################################################################################################
    ###### These Function adds every track from bdinfo list of tracks to a dictionary                              #
    #It also adds data about the source of the information, and where to output it                                 #
    ################################################################################################################

    def updateRawTracksDict(self, trackStrs, playlistNum, playlistFile, streams, source, output):
        tracks = []
        for index, currline in enumerate(trackStrs):
            index = index+2
            self._appendTrack(currline, index, tracks, source)
        for track in tracks:
            track["sourceDir"] = source
            track["sourceKey"] = utils.sourcetoShowName(source)
        self._expandRawTracksData(
            tracks, playlistNum, playlistFile, streams, source, output)
        self.addSource(source)

    def addSource(self, source):
        self._sources.append(utils.sourcetoShowName(source))

    ################################################################################################################
    #   Getter Functions
    ################################################################################################################

    @property
    def rawMediaTracksData(self):
        return self._rawMediaTracksData

    def filterBySource(self, key):
        return self._rawMediaTracksData.get(key)

    """
   Private
    """

    ################################################################################################################
    ###### These Functions are used to parse Data from String for the corresponding Track Type i.e Video, Audio,etc#
    ################################################################################################################

    def _videoParser(self, currline):
        tempdict = {}
        bdinfo = re.search(
            "(?:.*?: (.*))", currline).group(1)
        tempdict = self._defaultMediaDict(bdinfo)
        tempdict["type"] = "video"
        return tempdict

    def _audioParser(self, currline):
        tempdict = {}
        lang = self._medialang(currline)
        langcode = self._mediacode(lang)
        bdinfo = list(filter(lambda x: x != None, list(
            re.search("(?:.*?/ )(?:(.*?) \(.*)?(.*)?", currline).groups())))[0]
        tempdict = self._defaultMediaDict(bdinfo, langcode, lang)
        tempdict["type"] = "audio"
        tempdict["auditorydesc"] = False
        tempdict["original"] = False
        tempdict["commentary"] = False

        return tempdict

    def _audioCompatParser(self, currline):
        tempdict = {}
        lang = self._medialang(currline)
        langcode = self._mediacode(lang)
        bdinfo = re.search("(?:.*?)(?:\((.*?)\))", currline)
        if bdinfo == None:
            return
        bdinfo = list(filter(lambda x: x != None, list(bdinfo.groups()
                                                       )))
        if len(bdinfo) == 0:
            return
        bdinfo = bdinfo[0]
        tempdict = self._defaultMediaDict(bdinfo, langcode, lang)
        tempdict["type"] = "audio"
        tempdict["compat"] = True
        tempdict["auditorydesc"] = False
        tempdict["original"] = False
        tempdict["commentary"] = False
        return tempdict

    def _subParser(self, currline):
        tempdict = {}
        lang = self._medialang(currline)
        bdinfo = currline
        langcode = self._mediacode(lang)
        tempdict = self._defaultMediaDict(bdinfo, langcode, lang)
        tempdict["type"] = "subtitle"
        tempdict["sdh"] = False
        tempdict["textdesc"] = False
        tempdict["commentary"] = False
        return tempdict

    # Standard Track Data Helper
    def _defaultMediaDict(self, bdinfo, langcode=None, lang=None):
        tempdict = {}
        tempdict["bdinfo_title"] = bdinfo
        tempdict["langcode"] = langcode
        tempdict["lang"] = lang
        tempdict["compat"] = False
        tempdict["default"] = False
        tempdict["forced"] = False
        tempdict["machine_parse"] = []
        tempdict["length"] = None
        return tempdict

        ################################################################################################################
        ###### These Functions are Used to get the Language/Code of a Track                                            #
        ################################################################################################################

    def _medialang(self, currline):
        return re.search("(?:.*?: )(.*?)(?: /.*)", currline).group(1)

    def _mediacode(self, lang):
        try:
            return langcodes.standardize_tag(langcodes.find(lang))
        except:
            return

        ################################################################################################################
        ###### Adds Track to List                                                                                     #
        ################################################################################################################

    def _appendTrack(self, currline, index, tracks, source):
        tempdict = None
        tempdict2 = None
        match = re.search("([a-z|A-Z]*?):", currline, re.IGNORECASE).group(1)
        if match == "Video":
            tempdict = self._videoParser(currline)
        elif match == "Audio":
            tempdict = self._audioParser(currline)
            tempdict2 = self._audioCompatParser(currline)
        elif match == "Subtitle":
            tempdict = self._subParser(currline)
    # Try to Get Unique Key Values
        tempdict["index"] = index
        value = tempdict["bdinfo_title"] + \
            utils.sourcetoShowName(source) + str(tempdict["index"])
        key = xxhash.xxh32_hexdigest(value)
        post = tempdict["langcode"] or "vid"
        tempdict["key"] = f"{key}_{post}"
        tempdict["parent"] = None
        tempdict["child"] = None
        tracks.append(tempdict)
        if tempdict2 != None:
            tempdict2["index"] = index

            # Try to Get Unique Key Values
            value = tempdict2["bdinfo_title"] + \
                utils.sourcetoShowName(source) + str(tempdict2["index"])
            key = xxhash.xxh32_hexdigest(value)
            post = tempdict2["langcode"] or "vid"
            tempdict2["key"] = f"{key}_{post}"
            tempdict2["child"] = None
            tempdict2["parent"] = tempdict["bdinfo_title"]
            tempdict["child"] = tempdict2["bdinfo_title"]
            tempdict["parent"] = None
            tracks.append(tempdict2)

    # Primary Key are Basename Source
    # Tracks are Objects
    # Output is a a string
    def _expandRawTracksData(self, tracks, playlistNum, playlistFile, streams, source, output):
        self._rawMediaTracksData[utils.sourcetoShowName(source)] = {}
        self._rawMediaTracksData[utils.sourcetoShowName(source)]["tracks"] = tracks
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["outputDir"] = output
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["sourceDir"] = source
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["playlistNum"] = playlistNum
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["playlistFile"] = playlistFile
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["streamFiles"] = self._getStreamNames(streams)
        self._rawMediaTracksData[utils.sourcetoShowName(
            source)]["length"] = self._getStreamLength(streams)

      ################################################################################################################
      ###### get data from streams
      ################################################################################################################
    def _getStreamNames(self, streams):
       return list(map(lambda x: x["name"], streams))

    def _getStreamLength(self, streams):
        return utils.subArrowTime(utils.convertArrow(streams[-1]["end"], "HH:mm:ss.SSS"),
                                  utils.convertArrow(streams[0]["start"], "HH:mm:ss.SSS")).format("HH [hour] mm [Minutes] ss [Seconds] SSS [MicroSeconds]")
