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
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock

import datetime
import os.path


class Previewer(Video):

    nav_sliders = ObjectProperty(None)

    def on_load(self):
        self.nav_sliders.duration = self.duration    

        def play(dt): 
            self.state = 'play'
            self.eos = 'pause'
        
        Clock.schedule_once(play, 0.1)


class NavSliders(Widget):

    duration = NumericProperty(0)
    label_a = ObjectProperty(None)
    label_b = ObjectProperty (None)
    slider_a = ObjectProperty(None)
    slider_b = ObjectProperty(None)
    player = ObjectProperty(None)

    def on_duration(self, old, new):
        self.slider_a.disabled = False
        self.slider_b.disabled = False
        self.slider_a.range = 0, new
        self.slider_a.value = min(new, max(0, new - 20))
        self.slider_b.range = 0, new
        self.slider_b.value = min(self.slider_a.value + 12, new)
        start_td = datetime.timedelta(seconds=self.slider_a.value)
        self.label_a.text = str(start_td)[:10]
        end_td = datetime.timedelta(seconds=self.slider_b.value)
        self.label_b.text = str(end_td)[:10]            
        self.player.seek(self.slider_a.value / new)


class SourceFile(Widget):

    filename = StringProperty('')
    filesize = NumericProperty(0)
    datetime = StringProperty('')
    duration = StringProperty('')

    file_list = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    def __init__(self, shadowtrim, **kwargs):
        super(SourceFile, self).__init__(**kwargs)
        self.file_list = shadowtrim.file_list
        self.video_editor = shadowtrim.video_editor

        self._shadowtrim = shadowtrim

    def on_touch_up(self, touch):
        if 'button' in touch.profile and touch.button == 'left':
            if touch.x > self.x and touch.x < self.right and touch.y > self.y and touch.y < self.top:
                self.video_editor.filename = os.path.join(self._shadowtrim.source_dir, self.filename)
                self.video_editor.file = self


class FileList(Widget):

    grid = ObjectProperty(None)
    source_files = ListProperty(None)

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

            if len(files) > 30:
                break

        files.sort(key=lambda f: f['ctime'], reverse=True)

        for file in files:
            source_file = SourceFile(
                shadowtrim,
                filename=file['name'],
                filesize=file['size'],
                datetime=file['ctime'].strftime('%Y %B %d %H:%M:%S'),
                duration='null'
            )
            
            self.grid.add_widget(source_file)
            self.source_files.append(source_file)

        return source_dir


class VideoEditor(Widget):
    
    filename = StringProperty('nothing selected')
    file = ObjectProperty(None)
    nav_sliders = ObjectProperty(None)
    player = ObjectProperty(None)

    def on_file(self, old, new):        
        self.player.unload()
        self.player.source = self.filename

        Clock.schedule_once(lambda dt: self.player.on_load(), 0.45)


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















# import os.path
# # ffmpeg -i "D:\ShadowPlay\Rocket League\Rocket League 2018.07.15 - 20.25.33.135737.DVR.mp4" -vcodec copy -acodec copy -ss 55 -t 10 output.mp4

# source_dir = r'D:\ShadowPlay\Rocket League'
# dest_dir = r'D:\Projects\shadowtrim'

# input_file = os.path.join(source_dir, 'Rocket League 2018.07.15 - 20.25.33.135737.DVR.mp4')
# output_file = os.path.join(dest_dir, 'test.mp4')
