import subprocess

R = 0.5625
cw_scale = f"'ceil(max(iw,ih*{R})/2)*2'"
ch_scale = f"'ceil(max(ih,iw/{R})/2)*2'"

cw_crop = f"'ceil(min(iw,ih*{R})/2)*2'"
ch_crop = f"'ceil(min(ih,iw/{R})/2)*2'"

fc = f"[0:v]split[v1][v2];[v1]scale=w={cw_scale}:h={ch_scale}:force_original_aspect_ratio=increase,crop=w={cw_crop}:h={ch_crop},boxblur=40:5[bg];[v2]scale=w={cw_scale}:h={ch_scale}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"

cmd = [r'c:\source_code_new\backup\video-downloader-interface\desktop_v2\ffmpeg\ffmpeg.exe', '-f', 'lavfi', '-i', 'testsrc=s=1920x1080:d=1', '-filter_complex', fc, '-map', '[out]', '-vframes', '1', '-y', 'test_out.jpg']

print(' '.join(cmd))
res = subprocess.run(cmd, capture_output=True, text=True)
print('STDOUT:', res.stdout)
print('STDERR:', res.stderr[-500:])
