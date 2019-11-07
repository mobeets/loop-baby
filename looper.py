import sys
import queue
from trellis import Trellis
from osc_interface import OscSooperLooperInterface

BUTTON_MAP = {
    'A': 'undo',
    'B': 'mute',
    'E': 'pause',
    'F': 'record',
    'G': 'overdub',
    }

class Loop:
	def __init__(self):
		self.state = 'off'

	def update(self, state):
		# todo: check if state is being toggled...
		if state == 'record':
			color = 'red'
		elif state == 'overdub':
			color = 'red'
		elif state == 'mute':
			color = 'blue'
		return color

class Looper:
	def __init__(self, trellis, interface, q, nloops=2, button_map=BUTTON_MAP, debug=False):

		self.trellis = trellis
		self.interface = interface
		self.q = q
		self.debug = debug

		self.button_map = button_map
		self.nloops = nloops
		self.loops = [Loop() for i in range(nloops)]
		self.current_loop = 0

	def start():
		try:
	        while True:
	            self.trellis.sync()
	            # time.sleep(.02)

	            # get item from queue
	            (button, press_type) = self.q.get(block=False)
            	action = self.button_map.get(button, button)

	            # process message
            	if press_type == 'pressed':
            		if self.debug:
	            		print('Pressed {} -> {}'.format(button, action))

        			if action == 'pause':
        				"""
        				need to fix color
        				"""
            			self.interface.hit(action, self.current_loop)
            			color = 'green'
            			self.trellis.set_color(button, color)
            		
            		elif action in ['record', 'overdub', 'mute']:
            			"""
            			not right. might need to be multiple buttons changing color
            			"""
            			self.interface.hit(action, self.current_loop)
            			color = self.loops[self.current_loop].update(action)
            			self.trellis.set_color(button, color)
            		
            		elif type(action) is int:
            			self.interface.set('selected_loop_num', action)
            			self.current_loop = action
            			self.trellis.toggle_color(button, 'gray')

        		elif press_type == 'released':
        			if type(action) is int:
        				pass
        				# self.trellis.set_color(button, 'off')

	            # mark task as done
	            self.q.task_done()
	    except queue.Empty:
	        pass

def main():
	q = queue.Queue()
	trellis = Trellis(q)
    interface = OscSooperLooperInterface(q)
    looper = Looper(trellis, interface, q)
	try:
    	looper.start()
	except KeyboardInterrupt:
        # Properly close the system.
        interface.terminate()

if __name__ == '__main__':
	main()
