import wave
import os
import contextlib

def check_wav_files(directory):
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return

    print(f"{'Filename':<20} | {'Sample Rate (Hz)':<16} | {'Channels':<8} | {'Duration (s)':<12}")
    print("-" * 65)

    files = [f for f in os.listdir(directory) if f.lower().endswith('.wav')]
    if not files:
        print("No .wav files found.")
        return

    for filename in files:
        filepath = os.path.join(directory, filename)
        try:
            with contextlib.closing(wave.open(filepath, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                channels = f.getnchannels()
                duration = frames / float(rate)
                
                print(f"{filename:<20} | {rate:<16} | {channels:<8} | {duration:<12.2f}")
        except Exception as e:
            print(f"{filename:<20} | Error reading file: {e}")

if __name__ == "__main__":
    audio_dir = os.path.join(os.path.dirname(__file__), "Audio_files")
    check_wav_files(audio_dir)
