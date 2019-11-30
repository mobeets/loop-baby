
class Track:
    def __init__(self, track, client, button_number):
        self.track = track
        self.client = client
        self.button_number = button_number
        self.is_playing = False
        self.is_muted = False
        self.is_recording = False
        self.is_overdubbing = False
        self.is_pressed = False
        self.stopped_overdub_id = None
        self.stopped_record_id = None
        self.has_had_something_recorded = False

    def remute_if_necessary(self):
        """
        need to re-mute if this track was initially muted
        """
        if self.is_muted:
            self.client.hit('mute', self.track)

    def mark_as_muted(self):
        """
        after a oneshot, we will be auto-muted by SL, so we deal with it
        """
        self.is_muted = True

    def toggle_record(self):
        self.is_recording = not self.is_recording
        self.client.hit('record', self.track)
        self.has_had_something_recorded = True
        if not self.is_recording:
            # just stopped recording; check if we were muted
            self.remute_if_necessary()

    def toggle_overdub(self):
        self.is_overdubbing = not self.is_overdubbing
        self.client.hit('overdub', self.track)
        self.has_had_something_recorded = True
        if not self.is_overdubbing:
            # just stopped overdubbing; check if we were muted
            self.remute_if_necessary()

    def undo(self):
        self.client.hit('undo', self.track)

    def redo(self):
        self.client.hit('redo', self.track)

    def clear(self):
        self.client.hit('undo_all', self.track)
        self.has_had_something_recorded = False

    def toggle(self, mode, event_id=None):
        if mode == 'record':
            if self.stopped_record_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.toggle_record()
            return self.is_recording

        elif mode == 'overdub':
            if self.stopped_overdub_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.toggle_overdub()
            return self.is_overdubbing

        elif mode == 'pause':
            if self.is_playing:
                self.client.hit('pause_on', self.track)
            else:
                self.client.hit('pause_off', self.track)
            self.is_playing = not self.is_playing

        elif mode == 'mute':
            if self.is_muted:
                self.client.hit('mute_off', self.track)
            else:
                self.client.hit('mute_on', self.track)
            self.is_muted = not self.is_muted
            return self.is_muted

    def stop_record_or_overdub(self, event_id):
        """
        okay sorry, this is horrible, but every time a button
        is pressed, we will run this, which will check if the
        loop is recording (or overdubbing), and if it is,
        stop it, and mark the event_id that stopped it.

        the situation we need to handle is that the button
        that was pressed was a button explicitly trying to stop
        recording...so in toggle(), we only toggle something if
        the event_id's don't match
        """
        self.stopped_overdub_id = None
        self.stopped_record_id = None
        did_something = False
        if self.is_recording:
            self.toggle_record()
            self.stopped_record_id = event_id
            did_something = True
        elif self.is_overdubbing:
            self.toggle_overdub()
            self.was_stopped_overdubbing = True
            self.stopped_overdub_id = event_id
            did_something = True
        return did_something
