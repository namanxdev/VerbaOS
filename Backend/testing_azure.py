import requests
import json
import os
import base64
import glob
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
url = os.getenv('REST_END_POINT__HUBERT')
api_key = os.getenv('PRIMARY_KEY__HUBERT')

if not api_key:
    raise Exception("A key should be provided to invoke the endpoint. Check your .env file for PRIMARY_KEY__HUBERT.")

if not url:
    raise Exception("REST_END_POINT__HUBERT not found in .env file.")

# Get all audio files from Audio_files folder
audio_folder = os.path.join(os.path.dirname(__file__), 'Audio_files')
audio_files = sorted(glob.glob(os.path.join(audio_folder, '*.wav')))

print("=" * 70)
print("Testing Azure HuBERT endpoint - All Audio Files")
print("=" * 70)
print(f"Endpoint: {url}")
print(f"Audio folder: {audio_folder}")
print(f"Found {len(audio_files)} audio file(s)")
print("=" * 70)

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

results = []

for i, audio_file_path in enumerate(audio_files, 1):
    filename = os.path.basename(audio_file_path)
    print(f"\n[{i}/{len(audio_files)}] Processing: {filename}")
    
    # Read and encode the audio file as base64
    with open(audio_file_path, 'rb') as audio_file:
        audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    print(f"  Size: {len(audio_bytes)} bytes")
    
    # Prepare request data
    data = {
        "audio": audio_base64,
        "sample_rate": 16000
    }
    
    try:
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            transcription = result.get('transcription', 'N/A')
            print(f"  ✅ Transcription: {transcription}")
            results.append({
                'file': filename,
                'status': 'success',
                'transcription': transcription
            })
        else:
            print(f"  ❌ Failed (Status {response.status_code}): {response.text[:100]}")
            results.append({
                'file': filename,
                'status': 'error',
                'error': response.text[:100]
            })
            
    except requests.exceptions.Timeout:
        print(f"  ❌ Timeout")
        results.append({'file': filename, 'status': 'timeout'})
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection error: {e}")
        results.append({'file': filename, 'status': 'connection_error'})
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results.append({'file': filename, 'status': 'error', 'error': str(e)})

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
success_count = sum(1 for r in results if r['status'] == 'success')
print(f"Total: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")
print("\nAll Transcriptions:")
for r in results:
    if r['status'] == 'success':
        print(f"  {r['file']}: {r['transcription']}")
    else:
        print(f"  {r['file']}: [ERROR - {r['status']}]")