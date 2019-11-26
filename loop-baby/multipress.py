
class MultiPress:
    """
    looks for multiple-button commands, and when finds a match,
    it calls the corresponding callback
    """
    def __init__(self, commands=None, callbacks=None):
        self.commands = commands
        self.callbacks = callbacks

    def check_for_matches(self, buttons_pressed):
        for command, password in self.commands.items():
            if buttons_pressed.issuperset(password):
                # call the callback for this command
                self.callbacks[command]()
                # remove those keys from our buttons_pressed queue
                # so we can't execute this multiple times
                buttons_pressed.difference_update(password)
