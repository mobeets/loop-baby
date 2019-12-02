import time

def make_actions(sl_client, interface, button_map, meta_commands, settings_map):

    # make modes, loops, and sessions (the latter are indexed by track number)
    ntracks = len([x for x in button_map.values() if type(x) is int])
    actions = {'loops': [None]*ntracks, 'sessions': [None]*ntracks, 'modes': []}
    for button_number, name in button_map.items():
        if type(name) is int:
            actions['loops'][name-1] = Loop(name-1, button_number, interface, sl_client)
            actions['sessions'][name-1] = SessionButton(name-1, button_number, interface)
        else:
            actions['modes'].append(Button(name, button_number, interface))

    # make settings
    actions['settings'] = []
    for button_number, (param, name, value) in settings_map.items():
        actions['settings'].append(SettingsButton(param, name, value, button_number, interface, sl_client))

    actions['button_map'] = button_map
    actions['multipress'] = MultiPress(meta_commands)

    return actions

class Button:
    def __init__(self, name, button_number, interface):
        self.name = name
        self.button_number = button_number
        self.interface = interface

    def set_color(self, color):
        """
        color is str
        and can be either the color name, or a key to color_map
        """
        self.interface.set_color(self.button_number, color)

class SessionButton(Button):
    def __init__(self, name, button_number, interface):
        super().__init__(name, button_number, interface)
        self.pressed_once = False

class SettingsButton(Button):
    def __init__(self, param, name, value, button_number, interface, sl_client):
        super().__init__(name, button_number, interface)
        self.param = param
        self.value = value
        self.sl_client = sl_client
        self.is_set = False

    def set(self):
        if self.param is None:
            return
        self.is_set = True
        self.sl_client.set(self.param, self.value)

    def unset(self):
        if self.param is None:
            return
        self.is_set = False

class Loop(Button):
    def __init__(self, track, button_number, interface, sl_client):
        super().__init__(track, button_number, interface)
        self.track = track
        self.sl_client = sl_client
        self.reset_state()

    def reset_state(self):
        self.is_enabled = False
        self.is_playing = False
        self.is_muted = False
        self.is_recording = False
        self.is_overdubbing = False
        self.is_pressed = False
        self.stopped_overdub_id = None
        self.stopped_record_id = None
        self.pressed_once = False
        self.has_had_something_recorded = False

    def enable(self):
        self.is_enabled = True

    def disable(self):
        self.reset_state()

    def press(self):
        if not self.is_enabled:
            return
        self.is_pressed = True

    def unpress(self):
        if not self.is_enabled:
            return
        self.is_pressed = False

    def remute_if_necessary(self):
        """
        need to re-mute if this track was initially muted
        """
        if not self.is_enabled:
            return
        if self.is_muted:
            self.sl_client.hit('mute', self.track)

    def mark_as_muted(self):
        """
        after a oneshot, we will be auto-muted by SL, so we deal with it
        """
        if not self.is_enabled:
            return
        self.is_muted = True

    def toggle_record(self):
        if not self.is_enabled:
            return
        self.is_recording = not self.is_recording
        self.sl_client.hit('record', self.track)
        self.has_had_something_recorded = True
        if not self.is_recording:
            # just stopped recording; check if we were muted
            self.remute_if_necessary()

    def toggle_overdub(self):
        if not self.is_enabled:
            return
        self.is_overdubbing = not self.is_overdubbing
        self.sl_client.hit('overdub', self.track)
        self.has_had_something_recorded = True
        if not self.is_overdubbing:
            # just stopped overdubbing; check if we were muted
            self.remute_if_necessary()

    def undo(self):
        if not self.is_enabled:
            return
        self.sl_client.hit('undo', self.track)

    def redo(self):
        if not self.is_enabled:
            return
        self.sl_client.hit('redo', self.track)

    def clear(self):
        if not self.is_enabled:
            return
        self.sl_client.hit('undo_all', self.track)
        self.has_had_something_recorded = False

    def oneshot(self):
        # reset_sync_pos so that it always plays from the top
        self.sl_client.hit('reset_sync_pos', self.track)
        self.sl_client.hit('oneshot', self.track)
        # if will auto-mute when done, so let's just mark this
        # because we just have to deal with what SL wants
        self.mark_as_muted()

    def toggle(self, mode, event_id=None):
        if not self.is_enabled:
            return

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
                self.sl_client.hit('pause_on', self.track)
            else:
                self.sl_client.hit('pause_off', self.track)
            self.is_playing = not self.is_playing

        elif mode == 'mute':
            if self.is_muted:
                self.sl_client.hit('mute_off', self.track)
            else:
                self.sl_client.hit('mute_on', self.track)
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
        if not self.is_enabled:
            return
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

class MultiPress:
    """
    looks for multiple-button commands, and when finds a match,
    it calls the corresponding callback
    """
    def __init__(self, commands=None):
        """
        example:
            commands = {'name':
                {'command': [1, 2, 3],
                'callback': lambda: print('Hi')}
        """
        self.commands = commands
        self.nseconds_restart_delay = 7 # delay after restart

    def check_for_matches(self, buttons_pressed, looper):
        found_match = False
        for name, item in self.commands.items():
            if buttons_pressed.issuperset(item['command']):
                found_match = True
                # call the callback for this command
                looper.interface.set_color_all_buttons('off')
                looper.interface.sync()
                item['callback']()
                if item['restart_looper']:
                    # todo: color all keys red
                    for j in range(self.nseconds_restart_delay):
                        if j % 2 == 0:
                            color = 'red'
                        else:
                            color = 'off'
                        looper.interface.set_color_all_buttons(color)
                        time.sleep(1)
                    # wait a generous amount of time for startup.sh to finish
                    # clear loops and start from scratch
                    looper.interface.set_color_all_buttons('off')
                    looper.init_looper()
                # remove those keys from our buttons_pressed queue
                # so we can't execute this multiple times
                buttons_pressed.difference_update(item['command'])
        return buttons_pressed, found_match
