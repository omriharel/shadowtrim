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
from kivy.uix.slider import Slider
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock

import datetime
import os.path


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

    def __init__(self, **kwargs):
        super(Previewer, self).__init__(**kwargs)

    def on_duration(self, old, new):
        if new == 1.0:
            self.seek(0)
            self.volume = 0
            self.state = 'play'
            return
        
        print 'dope load {0}'.format(new)
        self.nav_sliders.duration = new

    def on_position(self, old, new):
        distance_from_end_seek = abs(new - self.nav_sliders.slider_b.value)        
        
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
    

    # def __init__(self, **kwargs):
    #     super(NavSliders, self).__init__(**kwargs)
        

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
                print 'resist the end'
                slider.value = self.slider_b.max - 5

            elif slider.value + 5 > self.slider_b.value:
                print 'push b forwards'
                self.slider_b.value = min(slider.value + 5, self.slider_b.max)
            
            

            else:
                self.player.seek(slider.value / self.duration)


        elif slider == self.slider_b:
            if slider.value < 5:
                print 'resist the beginning'
                slider.value = 5


            elif slider.value - 5 < self.slider_a.value:
                print 'push a backwards'
                self.slider_a.value = max(slider.value - 5, 0)

            
            else:
                self.player.seek(slider.value / self.duration)

        start_td = datetime.timedelta(seconds=self.slider_a.value)
        self.label_a.text = str(start_td)[:10]

        end_td = datetime.timedelta(seconds=self.slider_b.value)
        self.label_b.text = str(end_td)[:10]   

        

class SourceFile(Widget):

    filename = StringProperty()
    filesize = NumericProperty()
    datetime = StringProperty()
    duration = StringProperty()
    filepath = StringProperty()

    file_list = ObjectProperty(None)
    video_editor = ObjectProperty(None)

    def __init__(self, shadowtrim, **kwargs):
        super(SourceFile, self).__init__(**kwargs)
        self.file_list = shadowtrim.file_list
        self.video_editor = shadowtrim.video_editor

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left' and touch.is_double_tap:
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

            # temp limit to work faster
            if len(files) > 30:
                break

        files.sort(key=lambda f: f['ctime'], reverse=True)

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

    def on_file(self, old, new):
        if self.player.disabled:
            self.player.disabled = False
        
        self.player.state = 'stop'
        self.player.unload()
        self.player.source = new.filepath

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
