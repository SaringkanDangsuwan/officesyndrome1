import cv2
import mediapipe as mp
import numpy as np
import time

# --- 1. Initialize MediaPipe Pose and drawing utilities ---

# Setup MediaPipe Pose model
# min_detection_confidence: Minimum confidence value ([0.0, 1.0]) for a pose detection to be considered successful.
# min_tracking_confidence: Minimum confidence value ([0.0, 1.0]) for the pose landmarks to be tracked successfully.
# model_complexity: Complexity of the pose landmark model: 0, 1, or 2.
#   - 0: Fastest, less accurate.
#   - 1: Balanced speed and accuracy (recommended for most cases).
#   - 2: Slower, more accurate.
pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=1)

# Drawing utilities for visualizing landmarks and connections
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- 2. Helper function to calculate angle between three points ---
# This function calculates the angle (in degrees) formed by three points.
# The angle is calculated at the 'mid' point.
# Parameters:
#   - a: First point coordinates (e.g., [x1, y1])
#   - b: Mid point coordinates (e.g., [x2, y2]) - where the angle is formed
#   - c: End point coordinates (e.g., [x3, y3])
# Returns:
#   - angle: The calculated angle in degrees.
def calculate_angle(a, b, c):
    a = np.array(a) # First point
    b = np.array(b) # Mid point (vertex of the angle)
    c = np.array(c) # End point

    # Calculate vectors from the mid point
    ba = a - b
    bc = c - b

    # Calculate the cosine of the angle using the dot product formula
    # cos(theta) = (A . B) / (|A| * |B|)
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))

    # Ensure cosine_angle is within valid range [-1, 1] to prevent arccos errors
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

    # Calculate the angle in radians and convert to degrees
    angle = np.degrees(np.arccos(cosine_angle))

    return angle

# --- 3. Main function to analyze posture based on landmarks ---
# This function takes MediaPipe landmarks and image dimensions to determine posture.
# It applies simple rules based on angles and distances.
# Parameters:
#   - landmarks: MediaPipe PoseLandmarks object containing detected keypoints.
#   - image_width: Width of the input image/frame.
#   - image_height: Height of the input image/frame.
# Returns:
#   - posture_status: A string indicating the posture (e.g., "Correct Posture", "Incorrect Posture").
#   - text_color: RGB tuple for the text and bounding box color.
def analyze_posture(landmarks, image_width, image_height):
    posture_status = "Unknown"
    text_color = (0, 0, 0) # Default color (black)

    # Check if landmarks were detected
    if landmarks:
        try:
            # Extract coordinates of essential landmarks for upper body posture analysis.
            # MediaPipe provides normalized coordinates (0 to 1), so multiply by image dimensions
            # to get pixel coordinates.
            left_shoulder = [landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value].x * image_width,
                             landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value].y * image_height]
            right_shoulder = [landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value].x * image_width,
                              landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value].y * image_height]
            left_ear = [landmarks[mp.solutions.pose.PoseLandmark.LEFT_EAR.value].x * image_width,
                        landmarks[mp.solutions.pose.PoseLandmark.LEFT_EAR.value].y * image_height]
            right_ear = [landmarks[mp.solutions.pose.PoseLandmark.RIGHT_EAR.value].x * image_width,
                         landmarks[mp.solutions.pose.PoseLandmark.RIGHT_EAR.value].y * image_height]
            nose = [landmarks[mp.solutions.pose.PoseLandmark.NOSE.value].x * image_width,
                    landmarks[mp.solutions.pose.PoseLandmark.NOSE.value].y * image_height]
            
            # Note: For full posture analysis (e.g., back slouching, hip angle),
            # landmarks like Hips and Knees are crucial. Since we only see the upper body,
            # our analysis will focus on neck/head posture and shoulder symmetry.

            # --- Rule 1: Detect Forward Head Posture / Neck Strain ---
            # Concept: Analyze the angle formed by shoulder, ear, and nose.
            # A healthy posture would have the ear roughly aligned with the shoulder.
            # Forward head posture causes the ear to move significantly forward relative to the shoulder.
            # A smaller angle (e.g., shoulder-ear-nose) might indicate forward head or slouching.

            # Calculate angles for both sides of the neck
            angle_left_neck = calculate_angle(left_shoulder, left_ear, nose)
            angle_right_neck = calculate_angle(right_shoulder, right_ear, nose)

            # Threshold for forward head posture (These values need calibration!)
            # You should test this by sitting in correct and incorrect postures
            # and observing the calculated angle values to set appropriate thresholds.
            # Example: If correct posture gives ~170-180 degrees, and forward head gives ~150-160 degrees.
            THRESHOLD_NECK_FORWARD = 165 # If angle is less than this, consider it forward head/slouching

            if angle_left_neck < THRESHOLD_NECK_FORWARD or angle_right_neck < THRESHOLD_NECK_FORWARD:
                posture_status = "Incorrect Posture: Forward Head/Slouching"
                text_color = (0, 0, 255) # Red color for incorrect posture

            # --- Rule 2: Check for Shoulder Asymmetry (Leaning) ---
            # Concept: Compare the vertical (Y) position of the left and right shoulders.
            # Significant difference might indicate leaning to one side.
            shoulder_y_diff = abs(left_shoulder[1] - right_shoulder[1]) # Difference in Y-coordinates (height)

            # Threshold for shoulder asymmetry (Needs calibration!)
            # Example: If straight posture gives ~0-10 pixels difference, and leaning gives >20 pixels.
            THRESHOLD_SHOULDER_ASYMMETRY = 25 # If difference is greater than this, consider it leaning

            # Only check for leaning if not already flagged as forward head/slouching
            if posture_status != "Incorrect Posture: Forward Head/Slouching" and shoulder_y_diff > THRESHOLD_SHOULDER_ASYMMETRY:
                posture_status = "Incorrect Posture: Leaning Shoulder"
                text_color = (0, 0, 255) # Red color

            # --- Rule 3: Correct Posture ---
            # If no incorrect posture rules are triggered, assume correct posture.
            if posture_status == "Unknown":
                posture_status = "Correct Posture"
                text_color = (0, 255, 0) # Green color for correct posture

        except Exception as e:
            # print(f"Error during posture analysis: {e}") # Uncomment for debugging
            posture_status = "Cannot Analyze Posture (Missing Data/Error)"
            text_color = (0, 165, 255) # Orange color for analysis issues

    else:
        posture_status = "No Person Detected"
        text_color = (0, 165, 255) # Orange color if no person is found

    return posture_status, text_color

# --- 4. Start capturing video from webcam ---
# cv2.VideoCapture(0) opens the default webcam. If you have multiple cameras,
# you might need to try 1, 2, etc.
cap = cv2.VideoCapture(1)

# Check if the webcam was opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam. Please check if it's connected and not in use.")
    exit()

print("Webcam opened successfully. Press 'q' to quit.")

# Variables for calculating Frames Per Second (FPS)
prev_frame_time = 0
new_frame_time = 0

# --- 5. Main video processing loop ---
while cap.isOpened():
    # Read a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame. Exiting...")
        break

    # Flip the frame horizontally (like a mirror) for a more intuitive view
    frame = cv2.flip(frame, 1)

    # Convert the BGR image (OpenCV default) to RGB (MediaPipe requires RGB)
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Set the image to be writeable = False for better performance with MediaPipe
    image.flags.writeable = False

    # Process the image with MediaPipe Pose to detect landmarks
    results = pose.process(image)

    # Set the image back to writeable = True for drawing
    image.flags.writeable = True
    # Convert the image back to BGR for OpenCV display
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # --- 6. Draw results and analyze posture ---
    posture_status = "No Person Detected"
    text_color = (0, 165, 255) # Default orange color

    if results.pose_landmarks:
        # Draw the pose landmarks (skeleton) on the image
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                                  landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())

        # Analyze the posture using our custom function
        posture_status, text_color = analyze_posture(results.pose_landmarks.landmark, frame.shape[1], frame.shape[0])
    
    # --- 7. Display status and bounding box ---
    # Display the posture status text on the image
    cv2.putText(image, f"Status: {posture_status}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)

    # Draw a bounding box around the detected person
    if results.pose_landmarks:
        # Get all x and y coordinates of the detected landmarks
        x_coords = [landmark.x * frame.shape[1] for landmark in results.pose_landmarks.landmark]
        y_coords = [landmark.y * frame.shape[0] for landmark in results.pose_landmarks.landmark]

        # Calculate min/max x and y to form the bounding box
        if x_coords and y_coords: # Ensure there are coordinates to prevent errors
            min_x = int(min(x_coords)) - 10 # Add/subtract padding for better visual
            max_x = int(max(x_coords)) + 10
            min_y = int(min(y_coords)) - 10
            max_y = int(max(y_coords)) + 10

            # Draw the rectangle (bounding box) with the color based on posture status
            cv2.rectangle(image, (min_x, min_y), (max_x, max_y), text_color, 3) # Thickness of 3 pixels

    # Calculate and display FPS (Frames Per Second)
    new_frame_time = time.time()
    fps = 1 / (new_frame_time - prev_frame_time)
    prev_frame_time = new_frame_time
    cv2.putText(image, f"FPS: {int(fps)}", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA) # White color for FPS

    # Display the processed image in a window
    cv2.imshow('Posture Detection', image)

    # Wait for a key press. If 'q' is pressed, exit the loop.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- 8. Clean up and release resources ---
# Release the webcam
cap.release()
# Close all OpenCV windows
cv2.destroyAllWindows()
# Close the MediaPipe Pose model
pose.close()
