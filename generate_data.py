import os
import pyttsx3
import soundfile as sf
import sounddevice as sd
import numpy as np

# Output directory
output_dir = os.path.join("Backend", "Audio_files", "Synthetic")
os.makedirs(output_dir, exist_ok=True)

# Initialize TTS engine
engine = pyttsx3.init()

# Test phrases imitating patients
phrases = [
    ("help", "Help me please"),
    ("help", "I need help"),
    ("help", "Nurse please"),
    ("water", "Water please"),
    ("water", "I am thirsty"),
    ("water", "Need a drink"),
    ("emergency", "Emergency"),
    ("emergency", "I fell down"),
    ("emergency", "Chest pain"),
    ("yes", "Yes"),
    ("no", "No"),
    ("unknown", "What is the time"),
]

print(f"Generating synthetic audio in {output_dir}...")

for intent, text in phrases:
    filename = f"{intent}_{text.replace(' ', '_').lower()}.wav"
    filepath = os.path.join(output_dir, filename)
    
    # Save to temporary file (standard format)
    temp_file = "temp.wav"
    engine.save_to_file(text, temp_file)
    engine.runAndWait()
    
    # Process with soundfile/numpy instead of pydub to avoid audioop issues in Py3.13
    try:
        data, samplerate = sf.read(temp_file)
        
        # Convert to mono if needed
        if len(data.shape) > 1:
            data = data.mean(axis=1)
            
        # Resample to 16000 Hz (simple decimation/interpolation)
        # Note: Proper resampling needs scipy, but for TTS this is often acceptable
        # Or better: just read into correct rate if possible, but sf.read just reads file
        # If sampling rate is different, we must resample.
        
        target_rate = 16000
        
        if samplerate != target_rate:
             # Basic resampling using linear interpolation
             duration = len(data) / samplerate
             new_len = int(duration * target_rate)
             data = np.interp(
                 np.linspace(0.0, 1.0, new_len),
                 np.linspace(0.0, 1.0, len(data)),
                 data
             )
        
        # Save as 16-bit PCM WAV
        sf.write(filepath, data, target_rate, subtype='PCM_16')
        print(f"✅ Generated: {filename}")
        
    except Exception as e:
        print(f"❌ Failed to convert {filename}: {e}")

# Cleanup
if os.path.exists("temp.wav"):
    os.remove("temp.wav")

print("\nDone! Now use these files to test your API.")

