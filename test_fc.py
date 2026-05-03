import subprocess

cw = "'ceil(max(iw,ih*0.5625)/2)*2'"
ch = "'ceil(max(ih,iw/0.5625)/2)*2'"
fc = f"[0:v]split[v1][v2];[v1]scale=w={cw}:h={ch}:force_original_aspect_ratio=increase,crop=w={cw}:h={ch},boxblur=40:5[bg];[v2]scale=w={cw}:h={ch}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"

cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=s=1920x1080:d=1', '-filter_complex', fc, '-map', '[out]', '-vframes', '1', '-y', 'test_out.jpg']

print(' '.join(cmd))
res = subprocess.run(cmd, capture_output=True, text=True)
print('STDOUT:', res.stdout)
print('STDERR:', res.stderr)
