import hashlib
import imagehash
from PIL import Image
import ffmpeg
import os
import numpy as np

class VideoHasher:
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def calculate_perceptual_hashes(file_path: str, interval_sec: int = 1) -> list:
        """
        Extracts frames every `interval_sec` and calculates pHash.
        """
        try:
            # Probe to get duration
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            
            hashes = []
            # Extract frames
            # We can use ffmpeg to output images to pipe
            # But for simplicity in MVP, let's just pick a few timestamps
            timestamps = range(0, int(duration), interval_sec)
            
            for ts in timestamps:
                out, _ = (
                    ffmpeg
                    .input(file_path, ss=ts)
                    .filter('scale', 100, 100) # Small size for hashing
                    .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                    .run(capture_stdout=True, quiet=True)
                )
                
                # Create PIL Image from bytes
                import io
                img = Image.open(io.BytesIO(out))
                phash = str(imagehash.phash(img))
                hashes.append({'timestamp': ts, 'phash': phash})
                
            return hashes
        except Exception as e:
            print(f"Error calculating pHash: {e}")
            return []

    @staticmethod
    def compare_hashes(hashes1: list, hashes2: list) -> float:
        """
        Compare two lists of {timestamp, phash}.
        Returns average Hamming distance.
        """
        if not hashes1 or not hashes2:
            return 0.0
            
        total_dist = 0
        count = 0
        
        # Simple matching by index/timestamp
        # Assuming same length and intervals for MVP
        min_len = min(len(hashes1), len(hashes2))
        
        for i in range(min_len):
            h1 = imagehash.hex_to_hash(hashes1[i]['phash'])
            h2 = imagehash.hex_to_hash(hashes2[i]['phash'])
            total_dist += (h1 - h2)
            count += 1
            
        return total_dist / count if count > 0 else 0.0
