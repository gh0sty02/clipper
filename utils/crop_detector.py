import subprocess
import re
import cv2
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CropDetector:
    """Detect optimal crop position for vertical video"""
    
    def __init__(self, face_detection_enabled: bool = True):
        self.face_detection_enabled = face_detection_enabled
        
        if face_detection_enabled:
            try:
                # Try to load face cascade
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                
                if self.face_cascade.empty():
                    logger.warning("Failed to load face cascade, disabling face detection")
                    self.face_detection_enabled = False
            except Exception as e:
                logger.warning(f"Error loading face cascade: {e}, disabling face detection")
                self.face_detection_enabled = False
    
    def detect_crop_position(self, video_path: str, start_time: float, 
                           duration: float, method: str = 'auto') -> tuple:
        """
        Detect optimal crop position for video segment
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration to analyze in seconds
            method: 'auto', 'center', 'cropdetect', or 'face'
            
        Returns:
            Tuple of (x_position, detected_method_used)
        """
        
        if method == 'center':
            return self._center_crop(video_path), 'center'
        
        elif method == 'cropdetect':
            return self._cropdetect_method(video_path, start_time), 'cropdetect'
        
        elif method == 'face':
            if self.face_detection_enabled:
                x_pos = self._face_detection_method(video_path, start_time, duration)
                if x_pos is not None:
                    return x_pos, 'face'
            # Fallback to cropdetect if face detection fails
            return self._cropdetect_method(video_path, start_time), 'cropdetect'
        
        else:  # 'auto'
            # Try face detection first, fallback to cropdetect, then center
            if self.face_detection_enabled:
                x_pos = self._face_detection_method(video_path, start_time, duration)
                if x_pos is not None:
                    return x_pos, 'face'
            
            x_pos = self._cropdetect_method(video_path, start_time)
            if x_pos is not None:
                return x_pos, 'cropdetect'
            
            return self._center_crop(video_path), 'center'
    
    def _center_crop(self, video_path: str) -> int:
        """Get center crop position"""
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()
        
        return width // 2
    
    def _cropdetect_method(self, video_path: str, start_time: float) -> int:
        """Use FFmpeg cropdetect to find crop position"""
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', '2',  # Analyze 2 seconds
                '-vf', 'cropdetect=24:16:0',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                text=True,
                stderr=subprocess.STDOUT
            )
            
            # Extract crop values: crop=w:h:x:y
            matches = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', result.stdout)
            
            if matches:
                # Get the most common crop value (last one usually most stable)
                width, height, x, y = matches[-1]
                logger.info(f"Cropdetect found: crop={width}:{height}:{x}:{y}")
                return int(x) + int(width) // 2  # Return center of detected crop
            
            return None
            
        except Exception as e:
            logger.error(f"Cropdetect failed: {e}")
            return None
    
    def _face_detection_method(self, video_path: str, start_time: float, 
                               duration: float) -> int:
        """Use OpenCV face detection to find optimal crop position"""
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Set starting position
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(duration * fps)
            
            # Sample every 30 frames (approximately 1 per second at 30fps)
            sample_interval = 30
            face_positions = []
            
            frame_count = 0
            
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_interval == 0:
                    # Convert to grayscale for face detection
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect faces
                    faces = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    
                    if len(faces) > 0:
                        # Calculate center of all detected faces
                        centers = [x + w/2 for (x, y, w, h) in faces]
                        avg_center = np.mean(centers)
                        face_positions.append(avg_center)
                
                frame_count += 1
            
            cap.release()
            
            if face_positions:
                # Return median face position (more robust than mean)
                optimal_x = int(np.median(face_positions))
                logger.info(f"Face detection found optimal position: {optimal_x} (from {len(face_positions)} samples)")
                return optimal_x
            
            logger.info("No faces detected in video segment")
            return None
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return None


# Example usage
if __name__ == "__main__":
    detector = CropDetector(face_detection_enabled=True)
    
    video_path = "input.mp4"
    x_pos, method = detector.detect_crop_position(video_path, start_time=180, duration=120)
    
    print(f"Optimal crop position: {x_pos} (method: {method})")