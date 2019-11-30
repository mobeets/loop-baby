import time

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

    def check_for_matches(self, buttons_pressed, looper):
        for name, item in self.commands.items():
            if buttons_pressed.issuperset(item['command']):
                # call the callback for this command
                item['callback']()
                if item['restart_looper']:
                    # todo: color all keys red
                    # looper.interface.set_color_of_group('all', 'red')
                    # wait a generous amount of time for startup.sh to finish
                    time.sleep(7)
                    # clear loops and start from scratch
                    looper.init_looper()
                # remove those keys from our buttons_pressed queue
                # so we can't execute this multiple times
                buttons_pressed.difference_update(item['command'])
        return buttons_pressed
