# pip install webrtcvad-wheels resemblyzer soundfile numpy librosa
import os
import numpy as np
import soundfile as sf
import webrtcvad
import librosa
from resemblyzer import VoiceEncoder
from collections import deque
from numpy.linalg import norm

# -------- settings --------
FRAME_MS = 30                # 10/20/30 ms supported by WebRTC VAD
VAD_AGGR = 2                 # 0=least aggressive, 3=most
TARGET_SR = 16000            # resemblyzer expects 16k mono
EMB_WINDOW_SEC = 1.0         # ~1s voiced chunks for stable embeddings
SIM_THRESHOLD = 0.80         # create new speaker if below this
HOLD_CHUNKS = 2              # hysteresis: need 2 consecutive assignments to switch
# --------------------------

def cosine_sim(a, b):
    return float(np.dot(a, b) / (norm(a) * norm(b) + 1e-8))

def resample_if_needed(audio, sr, target_sr=TARGET_SR):
    if sr == target_sr:
        return audio
    return librosa.resample(audio, orig_sr=sr, target_sr=target_sr)

def frame_generator(audio16, sr, frame_ms=FRAME_MS):
    frame_len = int(sr * frame_ms / 1000)
    for i in range(0, len(audio16) - frame_len + 1, frame_len):
        yield audio16[i:i+frame_len]

def voiced_segments(audio16, sr, vad):
    """Yield contiguous voiced chunks (numpy arrays) using VAD."""
    frames = list(frame_generator(audio16, sr))
    voiced = []
    collecting = []
    for f in frames:
        # WebRTC expects 16-bit PCM bytes
        pcm = (np.clip(f, -1, 1) * 32767).astype(np.int16).tobytes()
        is_speech = vad.is_speech(pcm, sample_rate=sr)
        if is_speech:
            collecting.append(f)
        else:
            if collecting:
                voiced.append(np.concatenate(collecting))
                collecting = []
    if collecting:
        voiced.append(np.concatenate(collecting))
    return voiced

def chunk_by_duration(arr, sr, win_sec):
    n = len(arr)
    size = int(sr * win_sec)
    out = []
    i = 0
    while i + size <= n:
        out.append(arr[i:i+size])
        i += size
    if i < n and (n - i) > 0.6 * size:  # keep tail if reasonably long
        out.append(arr[i:n])
    return out

def load_audio(audio_path, start=None, end=None):
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in ['.m4a', '.mp3', '.mp4', '.aac']:
        if start is not None and end is not None:
            duration = end - start
            audio, sr = librosa.load(audio_path, sr=None, mono=True, offset=start, duration=duration)
        else:
            audio, sr = librosa.load(audio_path, sr=None, mono=True)
    else:
        audio, sr = sf.read(audio_path, dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if start is not None and end is not None:
            start_idx = int(start * sr)
            end_idx = int(end * sr)
            audio = audio[start_idx:end_idx]
    return audio, sr

def online_speaker_count(audio_path, start=None, end=None):
    audio, sr = load_audio(audio_path, start=start, end=end)
    audio = resample_if_needed(audio, sr, TARGET_SR)
    sr = TARGET_SR
    time_offset = start if start is not None else 0.0

    # VAD
    vad = webrtcvad.Vad(VAD_AGGR)
    voiced = voiced_segments(audio, sr, vad)

    # Encoder
    encoder = VoiceEncoder()  # uses CPU/GPU automatically if available

    # Online assignment state
    speakers = []           # list of centroids (np.array)
    counts = []             # number of chunks per speaker
    hold = deque(maxlen=HOLD_CHUNKS)  # recent labels for hysteresis

    timeline = []           # (start_sec, end_sec, speaker_id)
    cursor = 0.0           # time cursor in seconds

    for seg in voiced:
        seg_dur = len(seg) / sr
        # split to ~1s chunks to get embeddings
        chunks = chunk_by_duration(seg, sr, EMB_WINDOW_SEC)
        for ch in chunks:
            # get embedding for the chunk
            # (preprocess_wav does level normalization; here we provide raw 16k float)
            emb = encoder.embed_utterance(ch)

            # compare to existing speaker centroids
            if len(speakers) == 0:
                speakers.append(emb.copy())
                counts.append(1)
                label = 0
            else:
                sims = [cosine_sim(emb, c) for c in speakers]
                best_k = int(np.argmax(sims))
                if sims[best_k] >= SIM_THRESHOLD:
                    label = best_k
                    # update centroid (running mean)
                    counts[best_k] += 1
                    speakers[best_k] = speakers[best_k] + (emb - speakers[best_k]) / counts[best_k]
                else:
                    speakers.append(emb.copy())
                    counts.append(1)
                    label = len(speakers) - 1

            # hysteresis: require HOLD_CHUNKS consistent labels to switch
            hold.append(label)
            smoothed = max(set(hold), key=list(hold).count)

            # append to timeline (simple fixed-length chunk regions)
            start = cursor + time_offset
            end = cursor + len(ch) / sr + time_offset
            if timeline and timeline[-1][2] == smoothed:
                # extend current region
                s0, e0, k0 = timeline[-1]
                timeline[-1] = (s0, end, k0)
            else:
                timeline.append((start, end, smoothed))

            cursor = cursor + len(ch) / sr

        # account for any gap between voiced segments (silence)
        cursor += max(0.0, seg_dur - sum(len(c)/sr for c in chunks))

    num_speakers = len(speakers)
    return num_speakers, timeline

if __name__ == "__main__":
    path = "/Users/slimslavik/Downloads/New Recording 19.m4a"
    start_time = 0
    end_time = 690
    print(f"Processing segment {start_time}s-{end_time}s...")
    n_spk, tl = online_speaker_count(path, start=start_time, end=end_time)
    print("Estimated speakers:", n_spk)
    for s, e, k in tl:
        print(f"{s:.2f}s–{e:.2f}s  SPK_{k:02d}")
