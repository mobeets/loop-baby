import os.path
import glob
import xml.etree.ElementTree

class SLSessionManager:
    def __init__(self, session_dir, client, maxloops=8):
        self.session_dir = session_dir
        self.client = client
        self.maxloops = maxloops
        self.saved_sessions = self.prep_saved_sessions()

    def find_audiofiles_for_slsess_file(self, infile):
        """
        e.g., {0: "/home/pi/tmp.slsess_loop_00.wav"}
        """
        audiofiles = glob.glob(os.path.join(infile + '_loop_*.wav'))
        indices = [int(x.split('_loop_')[1].split('.wav')[0]) for x in audiofiles]
        return dict(zip(indices, audiofiles))

    def add_audio_paths_to_slsess_file(self, infile, audiofiles):
        """
        1. parse infile as xml
        2. for each Looper object:
        - add audiopath as loop_audio="..."
        - e.g., loop_audio="/home/pi/tmp.slsess_loop_00.wav"
        """
        et = xml.etree.ElementTree.parse(infile)
        loopers = et.find('Loopers')
        for index, looper in enumerate(loopers):
            if index in audiofiles:
                loopers[index].set('loop_audio', audiofiles[index])
            elif 'loop_audio' in loopers[index].keys():
                # file must have been deleted, because we didn't find it
                loopers[index].attrib.pop('loop_audio')
        et.write(infile)
        return len(loopers)

    def get_audio(self, infile):
        """
        find audio files for this slsess file
        then add the audio paths to the slsess file if they are not there
        """
        audiofiles = self.find_audiofiles_for_slsess_file(infile)
        nloops = self.add_audio_paths_to_slsess_file(infile, audiofiles)
        return {'audiofiles': audiofiles, 'nloops': nloops}

    def prep_saved_sessions(self):
        """
        look for slsess files, and corresponding audio files
        then inject the audio file paths into the slsess file,
            if it's not already present
        """
        saved_sessions = {}
        for i in range(self.maxloops):
            fnm = '{}.slsess'.format(i)
            infile = os.path.join(self.session_dir, fnm)
            saved_sessions[i] = {'session': infile, 'exists': False}
            if os.path.exists(infile):
                audio_info = self.get_audio(infile)
                saved_sessions[i].update(audio_info)
                saved_sessions[i]['exists'] = True
        return saved_sessions

    def session_exists(self, index):
        """
        check whether saved session file exists for this index
        """
        return self.saved_sessions[index]['exists']

    def save_session(self, index, loops):
        """
        save session in SL (.slsess); then save audio (.wav)
        """
        self.client.save_session(self.saved_sessions[index]['session'])
        # todo: save audio
        self.saved_sessions[index]['exists'] = True

    def load_session(self, index):
        """
        load the .slsess file (which contains links to audio files)
        return the number of loops we need to have
        """
        self.client.load_session(self.saved_sessions[index]['session'])
        return self.saved_sessions[index]['nloops']
