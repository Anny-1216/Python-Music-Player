from enum import nonmember
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import BooleanProperty,ObjectProperty
from pygame import mixer
import os
from mutagen.mp3 import MP3
from shutil import move
from mutagen.id3 import ID3, APIC
from kivy.uix.label import Label
from kivy.uix.button import Button
import pickle
import pandas as pd
mixer.init()
from kivy.lang import Builder
Builder.load_file('MusicApp.kv')

path = "Music"

class StartScreen(Screen):
    pass


class MainScreen(Screen):
    show_list = BooleanProperty(False)
    song = None
    song_name = ""
    song_path = ""
    song_list = []

    def toggle_song_list(self):
        """Toggle the visibility of the song list."""
        self.show_list = not self.show_list
        if self.show_list:
            self.populate_song_list()
        else:
            self.clear_song_list()

        full_screen = self.manager.get_screen('full')
        full_screen.song_list = self.get_song_list()

    def populate_song_list(self):
        """Populate the RecycleView with song data."""
        self.song_list = self.get_song_list()
        rv = self.ids.rv
        rv.data = [{"text": song, "on_press": lambda song=song: self.on_song_press(song)} for song in self.song_list]

    def clear_song_list(self):
        rv = self.ids.rv
        rv.data = []

    def get_song_list(self):
        """Fetch a list of .mp3 songs from the 'Music' directory."""
        if os.path.exists("Music"):
            return [filename for filename in os.listdir(path) if filename.endswith(".mp3")]
        else:
            return ["No songs found."]

    def on_song_press(self, song_name):
        playlist = self.manager.get_screen("playlist")
        playlist.is_playing = False
        self.song_path = os.path.join(path, song_name)
        self.song_name = song_name
        self.song = MP3(self.song_path)
        full_screen = self.manager.get_screen('full')
        full_screen.play(self.song_list.index(song_name))  



class FullScreen(Screen):
    paused_position = 0  # Store the paused position in milliseconds
    is_paused = False  # Flag to check if music is paused
    current_index = 0  # Keep track of the song index in the list
    song_name = ""
    song_list = []
    current_time = 0
    user_seeking = False


    def update_song(self):
        self.ids.song_label.text = self.song_name if self.song_name else "No song selected"
        ply = self.ids.play_time
        ply.text = "00:00"
        playlist = self.manager.get_screen("playlist")
        if playlist.is_playing:
            playlist.ids.message_label.text = self.song_name
            pass
        slide = self.ids.music
        self.current_time = 0
        slide.value = 0
        self.set_max_time()
        self.set_pic()

    def on_slider_value_change(self, instance, value):
        """Adjust the volume when the slider is moved."""
        mixer.music.set_volume(value / 100.0)  # Slider value is between 0 and 100

    def pause(self):
        """Pause the music and accumulate the current position immediately."""
        if mixer.music.get_busy() and not self.is_paused:  # Check if music is playing and not already paused
            mixer.music.pause()
            self.is_paused = True


    def un_pause(self):
        """Unpause the music from the accumulated paused position."""
        if self.is_paused:
            mixer.music.unpause()
            self.is_paused = False

        else:
            print("No song to unpause.")

    def set_pic(self):
        pass


    def start_seeking(self, touch):
        if self.ids.music.collide_point(*touch.pos):  # Check if touch is on the slider
            self.user_seeking = True
            if mixer.music.get_busy():
                mixer.music.pause()
                self.is_paused = True

    def seek(self, touch):
        if self.ids.music.collide_point(*touch.pos):  # Check if touch is on the slider
            self.user_seeking = False
            self.is_paused = False
            mixer.music.stop()
            self.current_time = self.ids.music.value
            print(self.current_time)
            lent = self.ids.play_time
            min, sec = self.get_time(self.current_time)
            lent.text = f"{min:02}:{sec:02}"
            mixer.music.play(start=self.current_time)



    def play(self, index):
        self.song_name = self.song_list[index]
        self.current_index = index
        self.current_song_path = os.path.join(path, os.path.basename(self.song_name))

        mixer.music.unload()
        mixer.music.load(self.current_song_path)
        mixer.music.play()
        self.update_song()

        Clock.schedule_interval(self.update_progress, 0.1)


    def update_progress(self, dt):
        if not self.user_seeking and not self.is_paused:
            if mixer.music.get_busy():
                current_time = self.current_time + mixer.music.get_pos() / 1000.0
                self.ids.music.value = current_time
                min, sec = self.get_time(current_time)
                self.ids.play_time.text = f"{min:02}:{sec:02}"

    def set_play_time(self):
        lent = self.ids.play_time
        length = mixer.music.get_pos()
        min, sec = self.get_time(length)
        lent.text = f"{min:02}:{sec:02}"


    def set_max_time(self):
        lent = self.ids.song_length
        song = MP3(self.current_song_path)
        total_length = song.info.length
        min, sec = self.get_time(total_length)
        slide = self.ids.music
        slide.max = total_length
        lent.text =  f"{min:02}:{sec:02}"


    def get_time(self, time):
        min = int(time // 60)
        sec = int(time % 60)
        return min, sec


    def play_next(self):
        """Play the next song in the list."""
        if self.song_list:
            self.current_index = (self.current_index + 1) % len(self.song_list)  # Loop to the beginning of the list
            self.play(self.current_index)

    def play_previous(self):
        """Play the previous song in the list."""
        if self.song_list:
            self.current_index = (self.current_index - 1) % len(self.song_list)  # Loop to the end of the list
            self.play(self.current_index)


class Playlist(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.playlists_dir = "playlists"
        self.mysongs_dir = "Music"
        self.playlist = []
        self.current_song_index = 0
        self.is_playing = False  # Track if a playlist is currently playing

    def create_playlist(self, instance):
        playlist_name = self.ids.playlist_name_input.text.strip()# Get user input
        if not playlist_name:
            self.ids.message_label.text = "Playlist name cannot be empty."
            return

        # Set the default path for playlists
        os.makedirs(self.playlists_dir, exist_ok=True)
        os.makedirs(self.mysongs_dir, exist_ok=True)
        playlist_path = os.path.join(self.playlists_dir, playlist_name)

        if os.path.exists(playlist_path):
            self.ids.message_label.text = f"Playlist '{playlist_name}' already exists!"
        else:
            os.makedirs(playlist_path)
            self.ids.message_label.text = f"Playlist '{playlist_name}' created successfully."

        self.ids.playlist_name_input.text = ""  # Clear input field
        self.refresh_playlists()

    def refresh_playlists(self):
        """Refresh the spinner with the latest playlists."""
        if os.path.exists(self.playlists_dir):
            playlists = [
                folder for folder in os.listdir(self.playlists_dir)
                if os.path.isdir(os.path.join(self.playlists_dir, folder))
            ]
            self.ids.playlist_spinner.values = playlists
        else:
            self.ids.playlist_spinner.values = []

    def add_song_to_playlist(self, instance):
        selected_playlist = self.ids.playlist_spinner.text
        if selected_playlist == "Select Playlist":
            self.ids.message_label.text = "Please select a playlist first."
            return

        selected_file = self.ids.file_chooser.selection
        if not selected_file:
            self.ids.message_label.text = "Please select a song to add."
            return

        song_path = selected_file[0]
        song_filename = os.path.basename(song_path)  # Get the song filename
        playlist_dir = os.path.join(self.playlists_dir, selected_playlist)
        song_dest_path = os.path.join(self.mysongs_dir, song_filename)

        try:
            # Move the file to the mysongs folder
            move(song_path, song_dest_path)

            # Record the song in the playlist's songs.txt file
            songs_file_path = os.path.join(playlist_dir, "songs.txt")
            with open(songs_file_path, "a") as f:
                f.write(song_dest_path + "\n")

            self.ids.message_label.text = f"Added song '{song_filename}' to '{selected_playlist}'."
        except Exception as e:
            self.ids.message_label.text = f"Error: {str(e)}"

    def play_playlist(self, instance):
        """Play the songs in the selected playlist."""
        if self.is_playing:
            self.ids.message_label.text = "A playlist is already playing. Please stop it first."
            return

        selected_playlist = self.ids.playlist_spinner.text
        if selected_playlist == "Select Playlist":
            self.ids.message_label.text = "Please select a playlist to play."
            return

        playlist_dir = os.path.join(self.playlists_dir, selected_playlist)
        songs_file_path = os.path.join(playlist_dir, "songs.txt")

        if not os.path.exists(songs_file_path):
            self.ids.message_label.text = "No songs in this playlist."
            return

        # Read songs from the playlist
        with open(songs_file_path, "r") as f:
            self.playlist = [line.strip() for line in f.readlines()]

        if not self.playlist:
            self.ids.message_label.text = "No songs found in the playlist."
            return

        self.is_playing = True
        self.current_song_index = 0
        self.play_current_song()


    def play_current_song(self):
        """Play the current song in the playlist."""
        if self.current_song_index >= len(self.playlist):
            self.ids.message_label.text = "Playlist finished."
            self.is_playing = False
            return

        full_screen = self.manager.get_screen("full")
        full_screen.song_list = self.playlist
        full_screen.play(self.current_song_index)

        # Schedule the next song to play when the current one finishes
        Clock.schedule_once(self.song_finished, 0.1)

    def song_finished(self, dt):
        """Called when the current song finishes playing, play the next song."""
        if not mixer.music.get_busy():
            self.current_song_index += 1
            self.play_current_song()

    def stop_playlist(self, instance):
        """Stop the currently playing playlist."""
        mixer.music.stop()
        self.is_playing = False
        self.ids.message_label.text = "Playlist stopped."

    def play_next_song(self, instance):
        """Play the next song in the playlist (circularly)."""
        if self.is_playing:
            full_screen = self.manager.get_screen("full")
            full_screen.play_next()
        else:
            self.ids.message_label.text = "No playlist is currently playing."





# Load the saved model (assuming similarity.pkl and df.pkl are in the same directory)
similarity = pickle.load(open('similarity.pkl', 'rb'))
df = pickle.load(open('df.pkl', 'rb'))

import pandas as pd

def recommendation(song_df):
    # Normalize input song title: strip spaces and lower case
    song_df = song_df.strip().lower()

    # Normalize the entire 'Title' column in df: strip spaces and lower case
    df['normalized_title'] = df['Title'].str.strip().str.lower()

    # Check if 'normalized_title' column exists
    if 'normalized_title' not in df.columns:
        raise KeyError("Column 'normalized_title' is missing from the DataFrame.")

    # Find matching song in the normalized 'Title' column
    matching_songs = df[df['normalized_title'] == song_df]

    if matching_songs.empty:
        raise ValueError(f"Song '{song_df}' not found in the dataset.")

    # Get the index of the song
    idx = matching_songs.index[0]

    # Ensure similarity matrix is valid
    if not similarity[idx].any():
        raise ValueError(f"No similarity scores found for song '{song_df}'.")

    # Calculate distances based on similarity
    distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])

    songs = []
    for m_id in distances[1:21]:
        songs.append(df.iloc[m_id[0]]['Title'])

    return songs



class rcmndsys(Screen):
    playlist_container = ObjectProperty(None)  # Reference to playlist container
    song_container = ObjectProperty(None)  # Reference to song container
    current_playlist = None
    def show_playlists(self):
        """Fetch and display playlists (directories) from 'playlists'."""
        playlists_dir = os.path.abspath("./playlists")
        self.ids.playlist_container.clear_widgets()  # Clear any existing widgets

        if os.path.exists(playlists_dir):
            playlists = [
                folder for folder in os.listdir(playlists_dir)
                if os.path.isdir(os.path.join(playlists_dir, folder))
            ]
            for playlist in playlists:
                btn = Button(text=playlist, size_hint_y=None, height=50)
                btn.bind(on_release=lambda btn, playlist=playlist: self.show_songs(playlist))
                self.ids.playlist_container.add_widget(btn)
        else:
            print("Playlists directory does not exist.")

    def show_songs(self, playlist_name):
        """Display the playlist name and songs in the right section."""
        self.current_playlist = playlist_name
        self.ids.playlist_container.clear_widgets()  # Remove playlist buttons

        # Add playlist name as a label to the song container
        self.ids.song_container.clear_widgets()  # Clear any existing song widgets
        self.ids.song_container.add_widget(Label(text=f"Playlist: {playlist_name}", size_hint_y=None, height=50))

        songs_file_path = os.path.join("./playlists", playlist_name, "songs.txt")

        if os.path.exists(songs_file_path):
            try:
                with open(songs_file_path, "r") as f:
                    songs = f.readlines()
                for song in songs:
                    song_button = Button(text=song.strip(), size_hint_y=None, height=50)
                    # Ensure that the correct song is passed to the function
                    song_button.bind(on_release=lambda btn, song=song.strip(): self.play_song(song))
                    self.ids.song_container.add_widget(song_button)
            except Exception as e:
                print(f"Error reading songs file for '{playlist_name}': {e}")
        else:
            print(f"Playlist '{playlist_name}' does not contain a songs.txt file.")

    def play_song(self, song_name):
        """Simulate playing a song."""
        print(f"Playing song: {song_name}")
        # Implement your actual song playback logic here
        # (e.g., using pygame or another audio library)

    def recommendsong(self):
        """
        Recommends songs based on the selected playlist.

        Args:
            playlist_name: The name of the playlist.

        Returns:
            A list of recommended songs.

        """
        if not self.current_playlist:
            print("No playlist selected for recommendations.")
            return []

        playlist_name = self.current_playlist
        songs_file_path = os.path.join("./playlists", playlist_name, "songs.txt")

        if os.path.exists(songs_file_path):
            try:
                with open(songs_file_path, "r") as f:
                    songs = f.readlines()
                    # Get the first song from the playlist for recommendation
                    input_song = songs[0].strip()
            except Exception as e:
                print(f"Error reading songs file for '{playlist_name}': {e}")
                return []

            # Recommend songs using the defined function
            song_path = input_song.replace("Music\\","")
            song_path = song_path.removeprefix(" ")
            song_path = song_path.removesuffix(".mp3")
            recommended_songs = recommendation(song_path)

            # Remove duplicates and limit to top 5 recommendations
            unique_recommendations = list(set(recommended_songs))[:5]

            # Display the recommendations (you can adjust this based on your UI)
            self.ids.song_container.clear_widgets() 
            for song in unique_recommendations:
                rec_button = Button(text=song, size_hint_y=None, height=50)
                self.ids.song_container.add_widget(rec_button)

            return unique_recommendations
        else:
            print(f"Playlist '{playlist_name}' does not contain a songs.txt file.")
            return []







class MusicApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StartScreen(name="start"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(FullScreen(name="full"))
        sm.add_widget(Playlist(name="playlist"))
        sm.add_widget(rcmndsys(name="rcmnd"))
        return sm

if __name__ == "__main__":
    MusicApp().run()
