import cv2
import glob
import os

video_dir = r"c:\Users\abhijeet.ansal\Desktop\purpelle\Resources\CCTV Footage-20260529T160731Z-3-00144614ea\CCTV Footage"
videos = glob.glob(os.path.join(video_dir, "*.mp4"))

print("Dataset Validation Report\n")
print(f"Found {len(videos)} video files.\n")

for vid_path in videos:
    cap = cv2.VideoCapture(vid_path)
    if not cap.isOpened():
        print(f"ERROR: Could not open {vid_path}")
        continue
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    duration = frame_count / fps if fps else 0
    
    name = os.path.basename(vid_path)
    print(f"--- {name} ---")
    print(f"Resolution : {width}x{height}")
    print(f"FPS        : {fps}")
    print(f"Frames     : {frame_count}")
    print(f"Duration   : {duration:.2f} seconds ({duration/60:.2f} minutes)")
    
    ret, frame = cap.read()
    if ret:
        frame_name = f"frame_{name.replace('.mp4', '.jpg')}"
        out_path = os.path.join(r"c:\Users\abhijeet.ansal\Desktop\purpelle\Resources", frame_name)
        cv2.imwrite(out_path, frame)
        print(f"Extracted first frame: {frame_name}")
    else:
        print("ERROR: Could not read first frame")
        
    cap.release()
    print()
