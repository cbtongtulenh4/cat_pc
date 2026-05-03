
import os

if __name__ == "__main__":
    _files = []
    folder = r"C:\source_code_new\backup\video-downloader-interface\demo_server\test"
    base_name = os.path.basename(folder)

    VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.3gp')
    for root, _, filenames in os.walk(folder):
        for f in sorted(filenames):
            if f.lower().endswith(VIDEO_EXTENSIONS):
                fp = os.path.normpath(os.path.join(root, f))
                if any(x['path'] == fp for x in _files):
                    continue
                
                rel_dir = os.path.relpath(root, folder)
                if rel_dir == ".":
                    rel_dir = base_name
                else:
                    rel_dir = os.path.join(base_name, rel_dir).replace("\\", "/")
                
                file_info = {
                    "path": fp,
                    "name": f,
                    "rel_dir": rel_dir,
                    "size": os.path.getsize(fp),
                    "duration": "...",
                    "status": "ready",
                    "checked": True
                }
                print(file_info)
