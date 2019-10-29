from midi import MidiConnector, Message, NoteOn, NoteOff

note_on = NoteOn(60, 100)
note_off = NoteOff(60, 100)

msg_on = Message(note_on, channel=1)
msg_off = Message(note_off, channel=1)

conn = MidiConnector('/dev/serial0', timeout=5)
conn.write(msg)
