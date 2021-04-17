import os
import sys
import csv

class Track:
    NAME_BUF = "_" * 256

    def __init__(self, track):
        self.Data = track
        self.Name = RPR_GetTrackName(self.Data, "_" * 256, 256)[2]
        self.Selected = RPR_GetMediaTrackInfo_Value(self.Data, "I_SELECTED") == 1

    def GetMediaItems(self):
        mediaItems = []
        numMediaItems = RPR_GetTrackNumMediaItems(self.Data)
        for i in range(numMediaItems):
            mediaItems.append(MediaItem(self, i))
        return mediaItems

class MediaItem:
    def __init__(self, track, index):
        self.Track = track
        self.Index = index
        self.Data = RPR_GetTrackMediaItem(self.Track.Data, self.Index)
        self.Position = RPR_GetMediaItemInfo_Value(self.Data, "D_POSITION")
        self.Length = RPR_GetMediaItemInfo_Value(self.Data, "D_LENGTH")
        self.Take = self.GetTakes()[0]

    def GetTakes(self):
        takes = []
        numTakes = RPR_GetMediaItemNumTakes(self.Data)
        for i in range(numTakes):
            takes.append(Take(self, i))
        return takes

class Take:
    METADATA_BUF = "_" * 1024
    FILENAME_BUF = "_" * 256

    def __init__(self, mediaItem, index):
        self.MediaItem = mediaItem
        self.Index = index
        self.Data = RPR_GetMediaItemTake(self.MediaItem.Data, self.Index)
        self.Source = RPR_GetMediaItemTake_Source(self.Data)
        self.Filename = self.GetFilename()
        self.Name = self.GetName()
        self.IsSection = False #placeholders...
        self.SectionOffset = 0
        self.SectionLength = 0
        self.Reverse = False
        self.GetSectionInfo() #section data is only valid if take is a section
        self.StartOffset = self.SectionOffset + RPR_GetMediaItemTakeInfo_Value(self.Data, "D_STARTOFFS") + (self.SectionLength * (1 if self.Reverse else 0))
        self.Playrate = RPR_GetMediaItemTakeInfo_Value(self.Data, "D_PLAYRATE")

    def GetMetadata(self):
        metadata = RPR_GetMediaFileMetadata(self.Source, "", Take.METADATA_BUF, len(Take.METADATA_BUF))
        return metadata

    def GetFilename(self):
        source = self.Source
        filename = ""
        while not filename:
            filename_d = RPR_GetMediaSourceFileName(source, Take.FILENAME_BUF, len(Take.FILENAME_BUF))
            filename = filename_d[1]
            #for sections or reversed clips, need to use the source parent instead
            source = RPR_GetMediaSourceParent(source)
        return filename

    def GetName(self):
        return os.path.splitext(os.path.basename(self.Filename))[0]

    def GetSectionInfo(self):
        #if the take is a section of another source, need to get some additional info
        sectionInfo = RPR_PCM_Source_GetSectionInfo(self.Source, self.SectionOffset, self.SectionLength, self.Reverse)
        self.IsSection = True if sectionInfo[0] else False
        if self.IsSection:
            self.SectionOffset = sectionInfo[2]
            self.SectionLength = sectionInfo[3]
            self.Reverse = True if sectionInfo[4] else False
            self.ReverseValue = -1 if self.Reverse else 1

class TimelineItem:
    def __init__(self, mediaItem):
        self.MediaItem = mediaItem
        self.TimelineStart = self.MediaItem.Position
        self.TimelineEnd = self.MediaItem.Position + self.MediaItem.Length
        self.Take = self.MediaItem.Take
        self.SourceStart = self.Take.StartOffset
        self.SourceEnd = self.Take.StartOffset + ((self.MediaItem.Length * self.Take.Playrate) * (-1 if self.Take.Reverse else 1))

    def ToString(self):
        itemName = os.path.basename(self.MediaItem.Take.GetFilename())
        return "{}:\n\tTimeline start: {}\n\tTimeline end: {}\n\tSource start: {}\n\tSource end: {}".format(itemName, self.TimelineStart, self.TimelineEnd, self.SourceStart, self.SourceEnd)

class ReaperTrackExport:
    EXPORT_FOLDER = "_tracks"

    def GetSelectedTrack():
        track = Track(RPR_GetSelectedTrack(0, 0))
        return track

    def GetSelectedTracks():
        return [track for track in ReaperTrackExport.GetTracks() if track.Selected]

    def GetTracks():
        tracks = []
        numTracks = RPR_GetNumTracks()
        for i in range(numTracks):
            track = Track(RPR_GetTrack(0, i))
            tracks.append(track)
        return tracks

    def GetTimelineItems(track):
        #returns a list of all items on the given track
        return [TimelineItem(mediaItem) for mediaItem in track.GetMediaItems()]

    def ExportTimelineItems(track, folder=None, selectionStart=None, selectionEnd=None):
        #get all timeline items from track
        timelineItems = ReaperTrackExport.GetTimelineItems(track)

        if selectionStart is not None and selectionEnd is not None:
            #filter to only items within the selected time
            timelineItems = [ti for ti in timelineItems if ti.TimelineStart >= selectionStart and ti.TimelineEnd <= selectionEnd]

        if folder is None:
            #get folder based on project path
            projectPath = RPR_GetProjectPath(' ' * 1024, 1024)[0]
            folder = os.path.join(projectPath, ReaperTrackExport.EXPORT_FOLDER)
            if not os.path.exists(folder):
                os.mkdir(folder)

        #write to csv
        filepath = os.path.join(folder, track.Name + ".csv")
        with open("{}".format(filepath), 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Name", "Source", "TimelineStart", "TimelineEnd", "SourceStart", "SourceEnd", "Playrate", "Reverse"])
            for ti in timelineItems:
                writer.writerow([ti.Take.GetName(), ti.Take.GetFilename(), ti.TimelineStart, ti.TimelineEnd, ti.SourceStart, ti.SourceEnd, ti.Take.Playrate, ti.Take.Reverse])

if __name__ == "__main__":
    selectedTracks = ReaperTrackExport.GetSelectedTracks()
    for selectedTrack in selectedTracks:
        ReaperTrackExport.ExportTimelineItems(selectedTrack)
    
    RPR_ShowMessageBox("Exported {} tracks to '{}' folder.".format(len(selectedTracks), ReaperTrackExport.EXPORT_FOLDER), "Success", 0)