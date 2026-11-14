"""GC-OS contract for the user-approved Final Master image, no alternative GUI."""
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"web"
class Scan(HTMLParser):
 def __init__(self):super().__init__();self.ids=set();self.duplicates=[];self.pages=set()
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if d.get("id"):
   if d["id"] in self.ids:self.duplicates.append(d["id"])
   self.ids.add(d["id"])
  if d.get("data-page"):self.pages.add(d["data-page"])
def run():
 html=(WEB/"gc-final.html").read_text()
 css=(WEB/"gc-final.css").read_text()
 js=(WEB/"gc-final.js").read_text()
 scan=Scan();scan.feed(html)
 assert not scan.duplicates,scan.duplicates
 assert set(["home","devices","climate","camera","growbook","rooms","homekit","cloud","more"])<=scan.pages
 assert set(["roomPicker","liveTiles","controlMount","homeCam","journalPreview","journalSelected","recentEvents","cloudLinkRow","homekitRow","cameraSettingsPanel"])<=scan.ids
 assert all(selector in css for selector in (".master-columns",".master-primary",".master-right",".hero-master",".tilegrid",".control-image",".journal-panel",".status-panel",".camera-panel",".integration-panel",".activity-panel"))
 assert "gc-hero-leaf.jpg" in css
 assert "mars-fc3000-transparent.png" in js
 assert "mars-df150m-hires.jpg" in js
 assert "loadJournal()" in js and "saveJournal(event)" in js
 assert all((WEB/a).is_file() for a in ("gc-hero-leaf.jpg","mars-fc3000-transparent.png","mars-df150m-hires.jpg","brand-mark.png"))
 assert all(example not in html and example not in js for example in ("24.6 °C","1320 RPM","2,5 L pro Topf"))
 assert css.count("{")==css.count("}")
 print("PASS: Final Master layout sections, real device images, journal binding, no mock values")
if __name__=="__main__":run()