import sys
import queue
from trellis import Trellis
from osc_interface import OscSooperLooperInterface

# {button_name: button_index_to_trellis, ...}
BUTTON_NAME_INVERSE = {
     1:  12,  2:   8,  3:  4,  4:  0,
     5:  13,  6:   9,  7:  5,  8:  1,
    'A': 14, 'B': 10, 'C': 6, 'D': 2,
    'E': 15, 'F': 11, 'G': 7, 'H': 3
    }
BUTTON_NAME_MAP = dict((BUTTON_NAME_INVERSE[key],key) for key in BUTTON_NAME_INVERSE)

BUTTON_GROUPS = {
	'mode_buttons': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
	'track_buttons': range(1,8),
	}

BUTTON_ACTION_MAP = {
    'A': 'oneshot',
    'B': 'save/recall',
    'C': 'clear',
    'D': 'settings',
    'E': 'play/pause',
    'F': 'record',
    'G': 'overdub',
    'H': 'mute',
    }

MODE_COLOR_MAP = {
	None: 'gray',
	'oneshot': 'green',
	'save': 'yellow',
	'recall': 'yellow',
	'clear': 'blue',
	'settings': 'gray',
	'play': 'green',
	'pause': 'yellow',
	'record': 'red',
	'overdub': 'orange',
	'mute': 'blue',
	}

class Loop:
	def __init__(self):
		self.state = 'off'

	def update(self, state):
		# todo: check if state is being toggled...
		assert False

	def toggle_play(self):
		assert False

class Looper:
	def __init__(self, trellis, interface, q, nloops=2,  debug=False, button_action_map=BUTTON_ACTION_MAP,
		button_name_map=BUTTON_NAME_MAP, button_groups=BUTTON_GROUPS,
		mode_color_map=MODE_COLOR_MAP):

		self.trellis = trellis
		self.interface = interface
		self.q = q
		self.debug = debug

		self.button_action_map = button_action_map
		self.nloops = nloops
		self.loops = [Loop() for i in range(nloops)]

		# define button groups
		self.button_name_map = button_name_map
		self.button_index_map = dict((v,k) for k,v in button_name_map.items())
		self.button_groups = button_groups
		for k,vs in self.button_groups.items():
			vs = [self.button_index_map[n] for n in vs]
			self.trellis.define_color_group(k, vs)
		self.mode_color_map = mode_color_map

		# state variables:
		self.current_loop = 0
		self.interface.set('selected_loop_num', self.current_loop)
		self.is_playing = False
		self.mode = None
		self.modes = [None, 'record', 'overdub', 'mute', 'oneshot',
			'save', 'load', 'clear', 'settings']

	def process_action(button_number, action, press_type):
        # updates happen at the time of button press
    	if press_type == 'pressed':
    		if type(action) is int:
    			self.process_track_change(action, button_number)
    		else:
    			self.process_mode_change(action, button_number)

    	# below we just manage colors upon button release
		elif press_type == 'released':
			if type(action) is int:
				if self.mode in [None, 'oneshot', 'clear']:
					# button press was a oneshot, so turn off light
					self.trellis.un_color(button_number)

	def process_mode_change(self, mode, button_number):
		"""
		the only mode that does something when pressed is 'play/pause'
		otherwise, we may need to handle button colors, but we otherwise
		just wait until a track button is pressed to do anything
		"""
		if self.debug:
    		print('Mode {} -> {}'.format(self.mode, mode))

		if mode == 'play/pause': # applies to all loops
			self.is_playing = not self.is_playing
			color = self.mode_color_map['play'] if self.is_playing else self.mode_color_map['pause']
			self.trellis.set_color(button_number, color)
			for i,loop in enumerate(self.loops):
				loop.toggle_play()
				# n.b. 'pause' will toggle between play/pause
				self.interface.hit('pause', i)
			return

		# changing to any other type of mode clears all buttons
		self.trellis.un_color('mode_buttons')
		self.trellis.un_color('track_buttons')
		previous_mode = self.mode
		
		if mode == 'save/recall': # toggles
			if previous_mode == 'save':
				mode = 'recall'
			else:
				mode = 'save'
		color = self.mode_color_map[mode]
		self.trellis.set_color(button_number, color)
		self.mode = mode

		if mode == 'clear':
			print('Clear mode not implemented yet.')

		elif mode == 'settings':
			print('Settings mode not implemented yet.')

		elif mode == 'save':
			print('Save mode not implemented yet.')
		
		elif mode == 'recall':
			print('Recall mode not implemented yet.')

	def process_track_change(self, track, button_number):
		"""
		actions depend on what mode we're in
		we also set button color based on the mode
		"""
		if self.debug:
			print('({}) track = {}'.format(self.mode, track))
		color = self.mode_color_map[self.mode]

		if self.mode == None:
			self.trellis.set_color(button_number, color)

		elif self.mode == 'oneshot':
			# warning: possible that hitting oneshot unpauses the track?
			self.current_loop = track
			self.interface.hit(self.mode, self.current_loop)
			self.trellis.set_color(button_number, color)

		elif self.mode in ['record', 'overdub']:
			self.current_loop = track
			self.interface.hit(self.mode, self.current_loop)
			self.trellis.set_color(button_number, color,
				uncolor='track_buttons')

		elif self.mode == 'save':
			print('Save not implemented yet.')
			self.trellis.set_color(track, color)

		elif self.mode == 'load':
			# if we press a track that isn't an option, do nothing
			print('Load track not implemented yet.')
			self.trellis.un_color(button_number)

		elif self.mode == 'clear':
			# if we press a track that isn't an option, do nothing
			print('Clear track not implemented yet.')
			self.trellis.un_color(button_number)

		elif self.mode == 'settings':
			print('Settings track not implemented yet.')
			self.trellis.un_color(button_number)

	def start(self):
		"""
		if this doesn't work, is multithreading what we want?
			1. trellis: syncs, pauses every 0.02, triggers callbacks
			2. looper: processes any callbacks triggered by trellis
		"""
		try:
	        while True:
	            self.trellis.sync()
	            # time.sleep(.02)

	            # act on message in queue
	            (button_number, press_type) = self.q.get(block=False)
	            button_name = self.button_names[button_number]
            	action = self.button_action_map.get(button_name, button_name)
            	if self.debug:
            		print('Button press: {} -> {} -> {}'.format(button_number, button_name, action))
				self.process_action(button_number, action, press_type)

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
