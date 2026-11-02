"""Generate the simple DRAP initial used by the installable app, not a new logo."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parent.parent/'web'/'icons'
root.mkdir(exist_ok=True)
for size,name in [(192,'icon-192.png'),(512,'icon-512.png'),(512,'maskable-512.png'),(180,'apple-touch-icon.png')]:
    image=Image.new('RGB',(size,size),'#4b5320');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',round(size*.49))
    bounds=draw.textbbox((0,0),'D',font=font)
    x=(size-(bounds[2]-bounds[0]))/2-bounds[0];y=(size-(bounds[3]-bounds[1]))/2-bounds[1]
    draw.text((x,y),'D',font=font,fill='#ffffff')
    image.save(root/name,optimize=True)
