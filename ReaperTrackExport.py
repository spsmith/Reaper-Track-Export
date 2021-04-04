import os
import sys
import csv

class Track:
    NAME_BUF = "_" * 256

    def __init__(self, track):
        self.Track = track
        self.Name = RPR_GetTrackName(self.Track, "_" * 256, 256)[2]
        self.Selected = RPR_GetMediaTrackInfo_Value(self.Track, "I_SELECTED") == 1

    def GetMediaItems(self):
        mediaItems = []
        numMediaItems = RPR_GetTrackNumMediaItems(self.Track)
        for i in range(numMediaItems):
            mediaItems.append(MediaItem(self.Track, i))
        return mediaItems

class MediaItem:
    def __init__(self, track, index):
        self.Track = track
        self.Index = index
        self.MediaItem = RPR_GetTrackMediaItem(self.Track, self.Index)
        self.Position = RPR_GetMediaItemInfo_Value(self.MediaItem, "D_POSITION")
        self.Length = RPR_GetMediaItemInfo_Value(self.MediaItem, "D_LENGTH")

    def GetTakes(self):
        takes = []
        numTakes = RPR_GetMediaItemNumTakes(self.MediaItem)
        for i in range(numTakes):
            takes.append(Take(self.MediaItem, i))
        return takes

class Take:
    METADATA_BUF = "_" * 1024
    FILENAME_BUF = "_" * 256

    def __init__(self, mediaItem, index):
        self.MediaItem = mediaItem
        self.Index = index
        self.Take = RPR_GetMediaItemTake(self.MediaItem, self.Index)
        self.Source = RPR_GetMediaItemTake_Source(self.Take)
        self.StartOffset = RPR_GetMediaItemTakeInfo_Value(self.Take, "D_STARTOFFS")
        self.Playrate = RPR_GetMediaItemTakeInfo_Value(self.Take, "D_PLAYRATE")

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

class TimelineItem:
    def __init__(self, mediaItem):
        self.MediaItem = mediaItem
        self.TimelineStart = self.MediaItem.Position
        self.TimelineEnd = self.MediaItem.Position + self.MediaItem.Length
        take = self.MediaItem.GetTakes()[0]
        self.SourceStart = take.StartOffset
        self.SourceEnd = take.StartOffset + (self.MediaItem.Length + take.Playrate)

    def ToString(self):
        itemName = os.path.basename(self.MediaItem.GetTakes()[0].GetFilename())
        return "{}:\n\tTimeline start: {}\n\tTimeline end: {}\n\tSource start: {}\n\tSource end: {}".format(itemName, self.TimelineStart, self.TimelineEnd, self.SourceStart, self.SourceEnd)

def GetSelectedTrack():
    track = Track(RPR_GetSelectedTrack(0, 0))
    return track

def GetSelectedTracks():
    return [track for track in GetTracks() if track.Selected]

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

if __name__ == "__main__":
    for selectedTrack in GetSelectedTracks():
        RPR_ShowMessageBox("{}".format('\n\n'.join([ti.ToString() for ti in GetTimelineItems(selectedTrack)])), "Timeline Items", 0)