import os
os.environ['KIVY_AUDIO'] = 'gstplayer'
os.environ['KIVY_AUDIO'] = 'gstplayer'

import kivy
kivy.require('1.9.1')

from kivy.config import Config
Config.setall('graphics', {
    'maxfps': '120',
    'height': '980',
    'width': '1800',
})
Config.set('kivy', 'log_level', 'debug')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.video import Video
from kivy.logger import Logger
from kivy.uix.slider import Slider
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock

import datetime
import os.path
import re
import subprocess
import shlex


class RichSlider(Slider):

    def __init__(self, **kwargs):
        self.register_event_type('on_release')
        super(RichSlider, self).__init__(**kwargs)

    def on_release(self):
        pass

    def on_touch_up(self, touch):
        super(RichSlider, self).on_touch_up(touch)
        if touch.grab_current == self:
            self.dispatch('on_release')
            return True


class Previewer(Video):

    nav_sliders = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    def on_duration(self, old, new):
        if new == 1.0:
            self.seek(0)
            self.volume = 0
            self.state = 'play'
            return
        
        self.nav_sliders.duration = new

    def on_position(self, old, new):
        distance_from_end_seek = abs(new - self.nav_sliders.slider_b.value)

        timedelta = datetime.timedelta(seconds=new)
        text = str(timedelta)[:10]
        if len(text) == 7:
            text += '.00'

        self.video_editor.position_label.text = text
        
        # loop if we reached slider b
        if new > 1 and distance_from_end_seek < 0.1 and self.state == 'play':
            self.seek(self.nav_sliders.slider_a.value / self.duration)


class NavSliders(Widget):

    duration = NumericProperty(0)
    label_a = ObjectProperty(None)
    label_b = ObjectProperty (None)
    slider_a = ObjectProperty(None)
    slider_b = ObjectProperty(None)
    player = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    def on_duration(self, old, new):

        # enable sliders if not active yet
        if self.slider_a.disabled:
            self.slider_a.disabled = False
            self.slider_b.disabled = False

            self.slider_a.bind(on_touch_down=self.suppress,
                               on_release=self.resume,
                               value=self.on_seek)

            self.slider_b.bind(on_touch_down=self.suppress,
                               on_release=self.loopback_and_resume,
                               value=self.on_seek)

        # set new ranges and potential play values according to movie duration
        self.slider_a.range = 0, new
        self.slider_b.range = 0, new

        a_value = min(new, max(0, new - 20))

        self.slider_b.value = min(a_value + 12, new)         
        self.slider_a.value = a_value
        
        # play from that point in the video
        self.player.seek(self.slider_a.value / float(new))
        self.player.state = 'play'
        self.player.volume = 1

    def suppress(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self.player.state = 'pause'

    def resume(self, slider):
        self.player.state = 'play'

        return True

    def loopback_and_resume(self, slider):
        self.player.seek(self.slider_a.value / self.duration)

        return self.resume(slider)

    def on_seek(self, slider, value):       
        if slider == self.slider_a:
            if slider.value + 5 > self.slider_b.max:
                slider.value = self.slider_b.max - 5

            elif slider.value + 5 > self.slider_b.value:
                self.slider_b.value = min(slider.value + 5, self.slider_b.max)

            elif self.slider_b.value - slider.value > 20:
                self.slider_b.value = slider.value + 20
            
            else:
                self.player.seek(slider.value / self.duration)


        elif slider == self.slider_b:
            if slider.value < 5:
                slider.value = 5

            elif slider.value - 5 < self.slider_a.value:
                self.slider_a.value = max(slider.value - 5, 0)

            elif slider.value - self.slider_a.value > 20:
                self.slider_a.value = slider.value - 20

            else:
                self.player.seek(slider.value / self.duration)

        start_td = datetime.timedelta(seconds=self.slider_a.value)
        self.label_a.text = str(start_td)[:10]

        end_td = datetime.timedelta(seconds=self.slider_b.value)
        self.label_b.text = str(end_td)[:10]

        duration_td = datetime.timedelta(seconds=self.slider_b.value - self.slider_a.value)
        text = str(duration_td)[:10]
        if len(text) == 7:
            text += '.00'
        
        self.video_editor.duration_label.text = text


class SourceFile(Widget):

    filename = StringProperty()
    filesize = NumericProperty()
    datetime = StringProperty()
    duration = StringProperty()
    filepath = StringProperty()

    mark_color_r = NumericProperty(0)
    mark_color_g = NumericProperty(0)
    mark_color_b = NumericProperty(0)
    mark_color_a = NumericProperty(0)
    mark_color = ReferenceListProperty(mark_color_r, mark_color_g, mark_color_b, mark_color_a)

    file_list = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    def __init__(self, shadowtrim, **kwargs):
        super(SourceFile, self).__init__(**kwargs)
        self.file_list = shadowtrim.file_list
        self.video_editor = shadowtrim.video_editor

    def mark_done(self):
        self.mark_color = 0.545, 0.909, 0.407, 0.85

    def mark_error(self):
        self.mark_color = 0.917, 0.262, 0.262, 0.85

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left' and touch.is_double_tap:
            self.file_list.select(self)
            self.video_editor.file = self


class FileList(Widget):

    grid = ObjectProperty(None)
    source_files = ListProperty(None)

    def select(self, source_file):
        wip_mark_color = 0.980, 0.678, 0.180, 0.85
        unselected_mark_color = 0, 0, 0, 0
        
        for file in self.source_files:
            if source_file.filepath == file.filepath and tuple(file.mark_color) in [unselected_mark_color, wip_mark_color]:
                source_file.mark_color = wip_mark_color

            elif tuple(file.mark_color) == wip_mark_color:
                file.mark_color = unselected_mark_color


    def create_source_files(self, shadowtrim):
        source_dir = os.getenv('SHADOWTRIM_SOURCE_DIR', r'D:\ShadowPlay\Rocket League')

        if not os.path.isdir(source_dir):
            raise SystemError('No such directory: {0}'.format(source_dir))
        
        ls = os.listdir(source_dir)
        files = []

        for filename in ls:
            if filename.endswith('.mp4'):
                statinfo = os.stat(os.path.join(source_dir, filename))
                ctime = datetime.datetime.fromtimestamp(statinfo.st_ctime)
                size = statinfo.st_size / 1000000000.0

                files.append({
                    'name': filename,
                    'size': size,
                    'ctime': ctime,
                })

            # # temp limit to work faster
            # if len(files) > 30:
            #     break

        files.sort(key=lambda f: f['ctime'])

        for file in files:
            source_file = SourceFile(
                shadowtrim,
                filename=file['name'],
                filesize=file['size'],
                datetime=file['ctime'].strftime('%Y %B %d %H:%M:%S'),
                duration='null',
                filepath=os.path.join(source_dir, file['name'])
            )
            
            self.grid.add_widget(source_file)
            self.source_files.append(source_file)

        return source_dir


class VideoEditor(Widget):

    file = ObjectProperty(None)
    nav_sliders = ObjectProperty(None)
    player = ObjectProperty(None)
    filename_input = ObjectProperty(None)
    save_button = ObjectProperty(None)
    duration_label = ObjectProperty(None)
    position_label = ObjectProperty(None)

    def validate_filename(self):
        self.player.state = 'pause'
        
        if not self._legal_filename(self.filename_input.text):
            self.filename_input.background_color = 0.8, 0, 0, 0.7
            self.filename_input.foreground_color = 0.7, 0.7, 0.7, 1

        else:
            self.filename_input.background_color = 1, 1, 1, 1
            self.filename_input.foreground_color = 0.3, 0.3, 0.3, 1

    def save_file(self):
        output_dir = os.getenv('SHADOWTRIM_OUTPUT_DIR', r'D:\ShadowPlay\Rocket League\trimmed')
        filename = self.filename_input.text
        if filename == '' or not self._legal_filename(filename):
            Logger.warning('Application: Illegal or empty filename')
            return

        original_filename = filename.rstrip('.mp4')
        filepath = os.path.join(output_dir, original_filename + '.mp4')
        starting_number = 2
        
        while os.path.exists(filepath):
            filepath = os.path.join(output_dir, original_filename + ' {0}.mp4'.format(starting_number))
            starting_number += 1

        start_time = self.nav_sliders.slider_a.value
        end_time = self.nav_sliders.slider_b.value
        
        Logger.info('Application: Saving file {0}'.format(filepath))
        Logger.debug('Application: Start position @ {0}'.format(self.nav_sliders.label_a.text))
        Logger.debug('Application: End position @ {0}'.format(self.nav_sliders.label_b.text))

        ffmpeg_command = 'ffmpeg -i "{source_file}" -vcodec copy -acodec copy -ss {start_position_seconds:.3f} -t {clip_duration:.3f} "{output_file}"'
        ffmpeg_command = ffmpeg_command.format(
            source_file=self.file.filepath,
            start_position_seconds=self.nav_sliders.slider_a.value,
            clip_duration=self.nav_sliders.slider_b.value - self.nav_sliders.slider_a.value,
            output_file=filepath
        )

        Logger.debug('Application: ffmpeg command: {0}'.format(ffmpeg_command))

        if self._run_command(ffmpeg_command):
            self.filename_input.text = ''
            self.file.mark_done()
            Logger.info('Application: Saved successfully!')
        else:
            self.file.mark_error()
            Logger.warning('Application: Error saving file!')

    def on_file(self, old, new):
        if self.player.disabled:
            self.player.disabled = False
            self.filename_input.disabled = False
        
        self.filename_input.text = ''
        self.player.state = 'stop'
        self.player.unload()
        self.player.source = new.filepath

    def _legal_filename(self, filename):
        return bool(re.match(r'^[a-zA-z0-9_\-()., ]*$', filename) and not filename.endswith('.'))

    def _run_command(self, command):
        popen = subprocess.Popen(['cmd.exe', '/c'] + shlex.split(command),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 cwd=os.getcwd(),
                                 env=os.environ)

        out, err = popen.communicate()
        code = popen.returncode

        if code != 0:
            Logger.warning('Application: Error running command: {0}'.format(command))
            Logger.warning('Application: Exit code: {0}'.format(code))
            Logger.warning('Application: Stdout: {0}'.format(out))
            Logger.warning('Application: Stderr: {0}'.format(err))
            
            return False

        Logger.debug('Application: Command executed successfully')
        Logger.trace('Application: Stdout: {0}'.format(out))
        
        return True


class JobStatuses(Widget):
    pass


class ShadowTrim(Widget):

    file_list = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    source_dir = StringProperty('')

    def initialize(self):
        self.source_dir = self.file_list.create_source_files(self)


class ShadowTrimApp(App):

    def build(self):
        shadowtrim = ShadowTrim()
        Clock.schedule_once(lambda dt: shadowtrim.initialize())
        return shadowtrim


if __name__ == '__main__':
    ShadowTrimApp().run()
