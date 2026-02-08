import subprocess
import re
import cv2
import numpy as np
from pathlib import Path
import logging
import mediapipe as mp
from typing import Optional, Tuple, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CropDetector:
    """Detect optimal crop position for vertical video using multiple methods"""
    
    def __init__(self, face_detection_enabled: bool = True, use_mediapipe: bool = True):
        self.face_detection_enabled = face_detection_enabled
        self.use_mediapipe = use_mediapipe
        
        # Initialize MediaPipe face detection
        self.mp_face_detection = None
        self.mp_drawing = None
        
        if face_detection_enabled and use_mediapipe:
            try:
                self.mp_face_detection = mp.solutions.face_detection
                self.mp_drawing = mp.solutions.drawing_utils
                logger.info("MediaPipe face detection initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe: {e}, falling back to OpenCV")
                self.use_mediapipe = False
        
        # Fallback to OpenCV Haar Cascade if MediaPipe fails or is disabled
        self.face_cascade = None
        if face_detection_enabled and not self.use_mediapipe:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                
                if self.face_cascade.empty():
                    logger.warning("Failed to load face cascade, disabling face detection")
                    self.face_detection_enabled = False
                else:
                    logger.info("OpenCV Haar Cascade face detection initialized")
            except Exception as e:
                logger.warning(f"Error loading face cascade: {e}, disabling face detection")
                self.face_detection_enabled = False
    
    def detect_crop_position(self, video_path: str, start_time: float, 
                           duration: float, method: str = 'auto') -> Tuple[int, str]:
        """
        Detect optimal crop position for video segment
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration to analyze in seconds
            method: 'auto', 'center', 'cropdetect', 'face', 'mediapipe', or 'hybrid'
            
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
                    detection_type = 'mediapipe' if self.use_mediapipe else 'opencv'
                    return x_pos, detection_type
            # Fallback chain
            x_pos = self._cropdetect_method(video_path, start_time)
            if x_pos is not None:
                return x_pos, 'cropdetect'
            return self._center_crop(video_path), 'center'
        
        elif method == 'mediapipe':
            if self.face_detection_enabled and self.use_mediapipe:
                x_pos = self._mediapipe_face_detection(video_path, start_time, duration)
                if x_pos is not None:
                    return x_pos, 'mediapipe'
            # Fallback
            x_pos = self._cropdetect_method(video_path, start_time)
            if x_pos is not None:
                return x_pos, 'cropdetect'
            return self._center_crop(video_path), 'center'
        
        elif method == 'hybrid':
            # Combine multiple methods for best accuracy
            return self._hybrid_detection(video_path, start_time, duration)
        
        else:  # 'auto'
            # Priority: MediaPipe > OpenCV > cropdetect > center
            if self.face_detection_enabled and self.use_mediapipe:
                x_pos = self._mediapipe_face_detection(video_path, start_time, duration)
                if x_pos is not None:
                    return x_pos, 'mediapipe'
            
            if self.face_detection_enabled and not self.use_mediapipe:
                x_pos = self._face_detection_method(video_path, start_time, duration)
                if x_pos is not None:
                    return x_pos, 'opencv'
            
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
    
    def _cropdetect_method(self, video_path: str, start_time: float) -> Optional[int]:
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
                stderr=subprocess.STDOUT,
                text=True
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
    
    def _mediapipe_face_detection(self, video_path: str, start_time: float, 
                                  duration: float) -> Optional[int]:
        """
        Use MediaPipe face detection for optimal crop position
        More accurate than Haar Cascades, provides confidence scores
        """
        try:
            face_positions = []
            confidences = []
            
            cap = cv2.VideoCapture(video_path)
            
            # Set starting position
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 30  # Default fallback
            total_frames = int(duration * fps)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            
            # Sample every 15 frames (~0.5s at 30fps) for performance
            sample_interval = 15
            
            with self.mp_face_detection.FaceDetection(
                model_selection=1,  # 1 = long range, better for small faces
                min_detection_confidence=0.5
            ) as face_detection:
                
                frame_count = 0
                samples_taken = 0
                
                while frame_count < total_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if frame_count % sample_interval == 0:
                        # Convert BGR to RGB for MediaPipe
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        rgb_frame.flags.writeable = False
                        
                        # Process face detection
                        results = face_detection.process(rgb_frame)
                        
                        if results.detections:
                            for detection in results.detections:
                                # Get relative bounding box
                                bbox = detection.location_data.relative_bounding_box
                                
                                # Convert to absolute coordinates
                                x_center = (bbox.xmin + bbox.width / 2) * frame_width
                                confidence = detection.score[0]
                                
                                face_positions.append(x_center)
                                confidences.append(confidence)
                                logger.debug(f"MediaPipe face: x={x_center:.1f}, conf={confidence:.2f}")
                        
                        samples_taken += 1
                    
                    frame_count += 1
            
            cap.release()
            
            if face_positions:
                # Weight by confidence if available
                if len(confidences) == len(face_positions) and any(c > 0 for c in confidences):
                    # Filter low confidence detections
                    valid_pairs = [(pos, conf) for pos, conf in zip(face_positions, confidences) if conf > 0.6]
                    if valid_pairs:
                        positions, weights = zip(*valid_pairs)
                        # Weighted median
                        optimal_x = int(np.average(positions, weights=weights))
                    else:
                        optimal_x = int(np.median(face_positions))
                else:
                    # Simple median (more robust than mean against outliers)
                    optimal_x = int(np.median(face_positions))
                
                logger.info(f"MediaPipe found optimal position: {optimal_x} "
                          f"(from {len(face_positions)} faces in {samples_taken} frames)")
                return optimal_x
            
            logger.info("No faces detected with MediaPipe in video segment")
            return None
            
        except Exception as e:
            logger.error(f"MediaPipe face detection failed: {e}")
            return None
    
    def _face_detection_method(self, video_path: str, start_time: float, 
                               duration: float) -> Optional[int]:
        """Use OpenCV Haar Cascade face detection (fallback method)"""
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
                logger.info(f"OpenCV face detection found optimal position: {optimal_x} "
                          f"(from {len(face_positions)} samples)")
                return optimal_x
            
            logger.info("No faces detected in video segment")
            return None
            
        except Exception as e:
            logger.error(f"OpenCV face detection failed: {e}")
            return None
    
    def _hybrid_detection(self, video_path: str, start_time: float, 
                          duration: float) -> Tuple[int, str]:
        """
        Combine multiple detection methods for best results
        Uses MediaPipe + cropdetect + temporal consistency check
        """
        candidates = []
        
        # Method 1: MediaPipe face detection
        if self.face_detection_enabled and self.use_mediapipe:
            mp_pos = self._mediapipe_face_detection(video_path, start_time, duration)
            if mp_pos is not None:
                candidates.append((mp_pos, 1.0, 'mediapipe'))  # Weight: 1.0
        
        # Method 2: OpenCV face detection (if MediaPipe disabled/failed)
        if self.face_detection_enabled and not self.use_mediapipe:
            cv_pos = self._face_detection_method(video_path, start_time, duration)
            if cv_pos is not None:
                candidates.append((cv_pos, 0.8, 'opencv'))  # Weight: 0.8
        
        # Method 3: FFmpeg cropdetect
        cd_pos = self._cropdetect_method(video_path, start_time)
        if cd_pos is not None:
            candidates.append((cd_pos, 0.6, 'cropdetect'))  # Weight: 0.6
        
        if not candidates:
            return self._center_crop(video_path), 'center'
        
        # If we have multiple candidates, use weighted average if they're close
        # Otherwise trust the highest confidence method
        if len(candidates) > 1:
            positions = [c[0] for c in candidates]
            max_diff = max(positions) - min(positions)
            
            # If methods agree within 20% of frame width, average them
            cap = cv2.VideoCapture(video_path)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            cap.release()
            
            if max_diff < frame_width * 0.2:
                # Weighted average
                total_weight = sum(c[1] for c in candidates)
                weighted_pos = sum(c[0] * c[1] for c in candidates) / total_weight
                methods_used = '+'.join(c[2] for c in candidates)
                logger.info(f"Hybrid detection: methods agree, weighted position: {int(weighted_pos)}")
                return int(weighted_pos), f'hybrid({methods_used})'
        
        # Return highest confidence single method
        best = max(candidates, key=lambda x: x[1])
        return best[0], best[2]
    
    def detect_with_temporal_smoothing(self, video_path: str, segments: List[Tuple[float, float]], 
                                       window_size: int = 3) -> List[Tuple[int, str]]:
        """
        Detect crop positions for multiple segments with temporal smoothing
        Prevents jarring jumps between adjacent segments
        """
        raw_positions = []
        
        for start, duration in segments:
            x_pos, method = self.detect_crop_position(video_path, start, duration, method='auto')
            raw_positions.append((x_pos, method))
        
        # Apply moving average smoothing
        smoothed = []
        for i, (pos, method) in enumerate(raw_positions):
            # Get window
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(raw_positions), i + window_size // 2 + 1)
            window = raw_positions[start_idx:end_idx]
            
            # Average positions
            avg_pos = int(np.mean([p[0] for p in window]))
            smoothed.append((avg_pos, method))
            
            if abs(avg_pos - pos) > 50:  # Log significant changes
                logger.info(f"Temporal smoothing: segment {i} adjusted from {pos} to {avg_pos}")
        
        return smoothed


# Example usage
if __name__ == "__main__":
    # Initialize with MediaPipe (recommended)
    detector = CropDetector(face_detection_enabled=True, use_mediapipe=True)
    
    video_path = "input.mp4"
    
    # Test different methods
    methods = ['auto', 'mediapipe', 'face', 'cropdetect', 'center', 'hybrid']
    
    for method in methods:
        x_pos, used_method = detector.detect_crop_position(
            video_path, 
            start_time=180, 
            duration=120, 
            method=method
        )
        print(f"Method '{method}': position={x_pos}, actually_used={used_method}")
    
    # Test temporal smoothing for multiple clips
    print("\n--- Temporal Smoothing Test ---")
    segments = [(0, 30), (30, 30), (60, 30), (90, 30)]  # 4 consecutive clips
    smoothed_positions = detector.detect_with_temporal_smoothing(video_path, segments)
    for i, (pos, method) in enumerate(smoothed_positions):
        print(f"Segment {i}: position={pos}, method={method}")