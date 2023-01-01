import itertools
import re
import os
import subprocess
from typing import  List,Union


import langcodes
from pymediainfo import MediaInfo


import src.tools.general as utils
import src.mediatools.mkvtoolnix as mkvTool
import src.tools.commands as commands
import src.tools.logger as logger
import src.tools.directory as dir
import src.tools.paths as paths


class MuxOBj():
    def __init__(self)->None:
        self._audio = []
        self._video = []
        self._sub = []
        self._out = None
        self._outputargs = []
        self._placeholder="PlaceHolderTitleRemux"

    def generateMuxData(self, remuxConfig:dict, outargs:List[str])->None:
        self._addAudioTracks(remuxConfig)
        self._addVideoTracks(remuxConfig)
        self._addSubTracks(remuxConfig)
        self._addOutPutArgs(outargs)
        self._out = list(itertools.chain.from_iterable(
            [self._video, self._audio, self._sub, self._outputargs]))

    @property
    def out(self)->List[str]:
        return self._out

    def _addVideoTracks(self, remuxConfig:dict)->None:
        out = []
        langcode = None
        try:
            langcodeKey = str(remuxConfig["Enabled_Tracks"]["Audio"][0])
            langcode = remuxConfig["Tracks_Details"]["Audio"][langcodeKey]["langcode"]
        except:
            langcode = langcodes.standardize_tag(
                langcodes.find(remuxConfig["Movie"]["languages"][0]))
        for i in range(len(remuxConfig["Enabled_Tracks"]["Video"])):
            key = remuxConfig["Enabled_Tracks"]["Video"][i]
            key = str(key)
            trackjson = remuxConfig["Tracks_Details"]["Video"][key]
            name = trackjson["site_title"]
            file = trackjson["filename"]

            temp = ["--language", f"0:{langcode}", "--compression", f"0:None"]
            if name:
                temp.extend(["--track-name", f"0:{name}"])

            default = ["--default-track-flag", "0:0"]
            if trackjson.get("default") == True:
                default = ["--default-track-flag", "0:1"]
            temp.extend(default)
            temp.append(file)
            out.append(temp)
        self._video = list(itertools.chain.from_iterable(out))

    def _addAudioTracks(self, remuxConfig:dict)->None:
        out = []
        for i in range(len(remuxConfig["Enabled_Tracks"]["Audio"])):
            key = remuxConfig["Enabled_Tracks"]["Audio"][i]
            key = str(key)
            trackjson = remuxConfig["Tracks_Details"]["Audio"][key]
            langcode = trackjson["langcode"]
            name = trackjson["site_title"]
            file = trackjson["filename"]
            temp = ["--language", f"0:{langcode}", "--compression", f"0:None"]
            if name:
                temp.extend(["--track-name", f"0:{name}"])

         # additional flags
            default = ["--default-track-flag", "0:0"]
            forced = ["--forced-display-flag", "0:0"]
            auditorydesc = ["--visual-impaired-flag", "0:0"]
            commentary = ["--commentary-flag", "0:0"]
            # reset flag values as needed

            if trackjson.get("default") == True:
                default = ["--default-track-flag", "0:1"]
            if trackjson.get("forced") == True:
                forced = ["--forced-display-flag", "0:1"]
            if trackjson.get("commentary") == True \
                    or re.search("commentary", name or "", re.IGNORECASE):
                commentary = ["--commentary-flag", "0:1"]
            if trackjson.get("auditorydesc") == True:
                auditorydesc = ["--visual-impaired-flag", "0:1"]
            temp.extend(default)
            temp.extend(forced)
            temp.extend(auditorydesc)
            temp.extend(commentary)
            temp.append(file)
            out.append(temp)
        self._audio = list(itertools.chain.from_iterable(out))

    def _addSubTracks(self, remuxConfig:dict)->None:
        out = []
        for i in range(len(remuxConfig["Enabled_Tracks"]["Sub"])):
            key = remuxConfig["Enabled_Tracks"]["Sub"][i]
            key = str(key)

            # get base data
            trackjson = remuxConfig["Tracks_Details"]["Sub"][key]
            langcode = trackjson["langcode"]
            file = trackjson["filename"]
            name = trackjson.get("site_title")
            temp = ["--language", f"0:{langcode}", "--compression", f"0:None"]
            if name:
                temp.extend(["--track-name", f"0:{name}"])
            # additional flags
            default = ["--default-track-flag", "0:0"]
            forced = ["--forced-display-flag", "0:0"]
            sdh = ["--hearing-impaired-flag", "0:0"]
            commentary = ["--commentary-flag", "0:0"]
            textdesc = ["--text-descriptions-flag", "0:0"]
            # flags values if needed
            if trackjson.get("default") == True:
                default = ["--default-track-flag", "0:1"]
            if trackjson.get("forced") == True:
                forced = ["--forced-display-flag", "0:1"]
            if trackjson.get("commentary") == True \
                    or re.search("commentary", name or "", re.IGNORECASE):
                commentary = ["--commentary-flag", "0:1"]
            if trackjson.get("sdh") == True \
                    or re.search("sdh", name or "", re.IGNORECASE):
                sdh = ["--hearing-impaired-flag", "0:1"]
            if trackjson.get("textdesc") == True \
                    or re.search("sdh", name or "", re.IGNORECASE):
                textdesc = ["--text-descriptions-flag", "0:1"]
            temp.extend(default)
            temp.extend(forced)
            temp.extend(sdh)
            temp.extend(commentary)
            temp.extend(textdesc)
            temp.append(file)
            out.append(temp)
        self._sub = (list(itertools.chain.from_iterable(out)))

    def getFileName(self,
                    remuxConfig:dict, group:str,title:str, episodeTitle:Union[str,None]=None)->str:
        episodeTitle=episodeTitle or self._placeholder
        videoCodec = mkvTool.getVideo(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        mediaType = mkvTool.getMediaType(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        videoRes = mkvTool.getVideoResolution(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])

        audioCodec = mkvTool.getAudio(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        audioChannel = mkvTool.getAudioChannel(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        year = remuxConfig['Movie']['year']
        season = remuxConfig["Movie"].get("season")
        episode = remuxConfig["Movie"].get("episode")
        movieName = f"{title} {year}"
        if season and episode:
            fileName = f"{movieName}.S{season//10}{season%10}E{episode//10}{episode%10}.{episodeTitle}.{videoRes}.{mediaType}.REMUX.{videoCodec}.{audioCodec}.{audioChannel}-{group}.mkv"
            return self._fileNameCleaner(fileName)

        else:
            fileName = f"{movieName}.{episodeTitle}.{videoRes}.{mediaType}.REMUX.{videoCodec}.{audioCodec}.{audioChannel}-{group}.mkv"
            return self._fileNameCleaner(fileName)


    def _fileNameCleaner(self, fileName:str)->str:
        fileName = re.sub(" +", " ", fileName)
        fileName = re.sub(" ", ".", fileName)
        fileName = re.sub("\.+", ".", fileName)
        fileName = re.sub("[@_!#$%^&*()<>?/\|}{~:]", "", fileName)
        fileName = re.sub("([^a-zA-Z\d])\.", ".", fileName)
        fileName = re.sub("\.([^a-zA-Z\d])", ".", fileName)
        fileName = re.sub(f"{self._placeholder}.", "",fileName)
        Noquotes = re.search('^"(.*)"$', fileName)
        if Noquotes:
            fileName = Noquotes.group(0)
        return fileName

    def _addOutPutArgs(self, outargs:str)->List[str]:
        self._outputargs = outargs.split()

    def createMKV(self, fileName:str, movieTitle:str, chapters:Union[str, bytes, os.PathLike], xml:Union[str, bytes, os.PathLike],  bdinfo:Union[Union[str, bytes, os.PathLike],None]=None, eac3to:Union[Union[str, bytes, os.PathLike],None]=None)->None:
        if os.path.exists(fileName):
            os.remove(fileName)
        command = list(itertools.chain.from_iterable(
            [commands.mkvmerge(), ["--title", movieTitle, "--chapters", chapters, "--output", fileName, "--global-tags", xml], self._out]))
        if chapters == None:
            command = list(itertools.chain.from_iterable(
                [commands.mkvmerge(), ["--title", movieTitle, "--output", fileName, "--global-tags", xml], self._out]))
        logger.logger.debug(f"Running This Command: \n{command}")
        logger.logger.debug(
            f"Running This CommandString :\n{' '.join(command)}")
        with subprocess.Popen(command, universal_newlines=True, stdout=subprocess.PIPE, bufsize=1) as p:
            for line in p.stdout:
                print(line, end='')

    def getTVDir(self, remuxConfig:dict, group:str, title:str)->str:
        videoCodec = mkvTool.getVideo(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        mediaType = mkvTool.getMediaType(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        videoRes = mkvTool.getVideoResolution(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])

        audioCodec = mkvTool.getAudio(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        audioChannel = mkvTool.getAudioChannel(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        year = remuxConfig['Movie']['year']
        season = remuxConfig["Movie"]["season"]
        movieName = f"{title} {year}"

        fileName = f"{movieName}.S{season//10}{season%10}.{videoRes}.{mediaType}.REMUX.{videoCodec}.{audioCodec}.{audioChannel}-{group}"
        # Normalize FileName
        return self._fileNameCleaner(fileName)

    def _getMovieDir(self, remuxConfig:dict, group:str, title:str, year:int)->str:
        videoCodec = mkvTool.getVideo(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        mediaType = mkvTool.getMediaType(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])
        videoRes = mkvTool.getVideoResolution(
            remuxConfig["Enabled_Tracks"]["Video"], remuxConfig["Tracks_Details"]["Video"])

        audioCodec = mkvTool.getAudio(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        audioChannel = mkvTool.getAudioChannel(
            remuxConfig["Enabled_Tracks"]["Audio"], remuxConfig["Tracks_Details"]["Audio"])
        movieName = f"{title} {year}"

        fileName = f"{movieName}.{videoRes}.{mediaType}.REMUX.{videoCodec}.{audioCodec}.{audioChannel}-{group}"
        # Normalize FileName
        return self._fileNameCleaner(fileName)

    def confirmName(self, fileName:str)->str:
        inputs = ["YES", "NO"]
        choice = utils.singleSelectMenu(
            inputs, f"Is this FilePath Correct: {fileName}\n")
        while choice != "YES":
            message = "Enter New FilePath: "
            fileName = utils.textEnter(message, fileName)
            choice = utils.singleSelectMenu(
                inputs, "Is the File Correct Now\n")
        return fileName

    def printMediaInfo(self, fileName:str)->None:
        with dir.cwd(paths.createTempDir()):
            print(MediaInfo.parse(fileName, output="", full=False))
