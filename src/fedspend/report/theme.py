"""Design tokens and stylesheet for the dashboard.

Kept separate from the page assembly so the visual system can be reviewed and
changed on its own.

Type
    Source Serif 4 carries the headline claims — a text serif in the register of
    a published report rather than a product page. IBM Plex Sans takes running
    text and UI; it was drawn for technical documentation, which is what this is.
    IBM Plex Mono carries every figure, code and piece of metadata, so numbers
    align and FPDS codes read as codes. Each stack names a real fallback, so the
    page keeps its layout if the font stylesheet never loads.

Colour
    Neutrals are biased cool, toward the blue accent, rather than left as a
    default mid-grey. The four series hues are validated for colour-vision
    -deficiency separation and surface contrast in both light and dark modes;
    orange is reserved for the emphasised mark, red/blue for the diverging pair,
    and the status colours are kept distinct from all of them.

Themes
    Three states are handled: bare ``:root`` defines the complete light palette;
    ``@media (prefers-color-scheme: dark)`` guarded by ``:not([data-theme="light"])``
    covers the un-stamped system-dark case; ``:root[data-theme="dark"]`` lets an
    explicit toggle win. No colour is defined only inside a media or attribute
    block.
"""

from __future__ import annotations

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=IBM+Plex+Mono:wght@400;500&amp;"
    "family=IBM+Plex+Sans:wght@400;500;600&amp;"
    'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&amp;display=swap">'
)

CSS = """
*,*::before,*::after{box-sizing:border-box}

:root{
  color-scheme:light;
  --surface-0:#f4f6f8; --surface-1:#ffffff; --surface-2:#e9edf1;
  --border:#d8dee5; --border-strong:#b6c1cc;
  --text-primary:#0d1418; --text-secondary:#48555f; --text-muted:#6d7c88;
  --series-1:#2a78d6; --series-2:#eb6834; --series-3:#1baf7a;
  --diverge-pos:#2a78d6; --diverge-neg:#e34948;
  --status-good:#0ca30c; --status-critical:#d03b3b;
  --grid:#e3e8ed;
  --shadow:0 1px 2px rgba(13,20,24,.05),0 10px 28px rgba(13,20,24,.05);
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif;
  --sans:"IBM Plex Sans",ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --surface-0:#0e1216; --surface-1:#161b21; --surface-2:#1e242b;
    --border:#2a323a; --border-strong:#3d4854;
    --text-primary:#f2f5f7; --text-secondary:#b3bfc9; --text-muted:#8593a0;
    --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
    --diverge-pos:#3987e5; --diverge-neg:#e66767;
    --grid:#242c34;
    --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 28px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --surface-0:#0e1216; --surface-1:#161b21; --surface-2:#1e242b;
  --border:#2a323a; --border-strong:#3d4854;
  --text-primary:#f2f5f7; --text-secondary:#b3bfc9; --text-muted:#8593a0;
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
  --diverge-pos:#3987e5; --diverge-neg:#e66767;
  --grid:#242c34;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 28px rgba(0,0,0,.35);
}

body{
  margin:0; background:var(--surface-0); color:var(--text-primary);
  font:400 15.5px/1.65 var(--sans); -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1040px;margin:0 auto;padding:44px 22px 84px;display:flex;flex-direction:column;gap:40px}

header.masthead{display:flex;flex-direction:column;gap:14px;
                border-bottom:2px solid var(--text-primary);padding-bottom:24px}
.eyebrow{font:500 11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--text-muted)}
h1{font:700 clamp(30px,4.6vw,46px)/1.08 var(--serif);margin:0;letter-spacing:-.015em;
   text-wrap:balance;max-width:21ch}
.standfirst{font-size:17.5px;color:var(--text-secondary);max-width:64ch;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:7px 16px;font:400 11.5px/1.5 var(--mono);color:var(--text-muted)}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(184px,1fr));gap:12px}
.kpi{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;
     padding:16px 17px 15px;display:flex;flex-direction:column;gap:5px;box-shadow:var(--shadow)}
.kpi .label{font:500 10.5px/1.3 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--text-muted)}
.kpi .value{font:600 29px/1 var(--serif);letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:12.5px;color:var(--text-secondary);line-height:1.4}
.kpi .sub.up{color:var(--status-critical)}
.kpi .sub.down{color:var(--status-good)}

section{margin:0}
.finding{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;
         padding:28px;box-shadow:var(--shadow);display:flex;flex-direction:column}
.tag{align-self:flex-start;font:500 10.5px/1 var(--mono);letter-spacing:.11em;
     text-transform:uppercase;color:var(--series-1);margin-bottom:13px}
h2{font:600 clamp(20px,2.5vw,25px)/1.25 var(--serif);margin:0 0 12px;letter-spacing:-.01em;
   text-wrap:balance;max-width:36ch}
h3{font:500 11px/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;
   color:var(--text-muted);margin:28px 0 10px}
p{margin:0 0 13px;color:var(--text-secondary);max-width:70ch}
p:last-of-type{margin-bottom:0}
p strong,li strong{color:var(--text-primary);font-weight:600}

.chart-frame{margin:20px 0 6px;overflow-x:auto}
svg.chart{display:block;width:100%;height:auto;min-width:520px}
.grid{stroke:var(--grid);stroke-width:1}
.zero{stroke:var(--border-strong);stroke-width:1.5}
.reference{stroke:var(--text-muted);stroke-width:1.5;stroke-dasharray:5 4}
.reference-label{font:400 11px var(--mono);fill:var(--text-muted)}
.line{fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.marker{stroke:var(--surface-1);stroke-width:2}
.bar{stroke:var(--surface-1);stroke-width:1}
.range,.range-cap{stroke:var(--text-muted);stroke-width:1.5}
.tick{font:400 11px var(--mono);fill:var(--text-muted)}
.row-label{font:400 12px var(--sans);fill:var(--text-secondary)}
.value-label{font:400 11.5px var(--mono);fill:var(--text-secondary)}
.direct-label{font:500 12px var(--mono)}
.crosshair{stroke:var(--border-strong);stroke-width:1;stroke-dasharray:3 3;opacity:0}
.hover-col{fill:transparent}
.hover-col:hover + .crosshair{opacity:.85}
.legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12.5px;color:var(--text-secondary)}
.legend-item{display:inline-flex;align-items:center;gap:7px}
.legend i,.tt-row i{width:11px;height:11px;border-radius:3px;display:inline-block;flex:none}

details{margin-top:18px;border-top:1px solid var(--border);padding-top:13px}
summary{cursor:pointer;font:500 11.5px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;
        color:var(--text-muted);list-style:none;padding:3px 0}
summary::-webkit-details-marker{display:none}
summary::before{content:"+ ";font-weight:600}
details[open] summary::before{content:"- "}
summary:hover{color:var(--series-1)}
summary:focus-visible{outline:2px solid var(--series-1);outline-offset:3px;border-radius:3px}
.table-scroll{overflow-x:auto;margin-top:14px}
table{border-collapse:collapse;width:100%;font:400 12.5px/1.5 var(--mono);font-variant-numeric:tabular-nums}
th,td{text-align:right;padding:8px 11px;border-bottom:1px solid var(--border);white-space:nowrap}
th:first-child,td:first-child{text-align:left;font-family:var(--sans)}
thead th{color:var(--text-muted);font:500 10.5px/1.3 var(--mono);letter-spacing:.07em;
         text-transform:uppercase;border-bottom:1.5px solid var(--border-strong);
         position:sticky;top:0;background:var(--surface-1)}
tbody tr:hover{background:var(--surface-2)}
.pos{color:var(--diverge-pos)}
.neg{color:var(--diverge-neg)}

.callout{border-left:2px solid var(--series-2);background:var(--surface-2);padding:14px 18px;
         border-radius:0 8px 8px 0;margin:18px 0 0}
.callout p{margin:0;color:var(--text-secondary)}
ul{margin:0;padding-left:19px;color:var(--text-secondary);display:flex;flex-direction:column;gap:9px}
footer{padding-top:24px;border-top:1px solid var(--border);font:400 12px/1.65 var(--mono);
       color:var(--text-muted)}
footer p{margin:0;max-width:78ch;color:inherit}
code{font:400 .92em var(--mono);background:var(--surface-2);padding:1.5px 5px;
     border-radius:4px;color:var(--text-secondary)}
.meta code{background:none;padding:0}

#tip{position:fixed;pointer-events:none;opacity:0;transition:opacity .1s;z-index:99;
     background:var(--surface-1);border:1px solid var(--border-strong);border-radius:8px;
     padding:10px 13px;font:400 12.5px/1.5 var(--sans);color:var(--text-primary);
     box-shadow:var(--shadow);max-width:290px}
#tip .tt-row{display:flex;align-items:center;gap:7px;color:var(--text-secondary);
             margin-top:4px;font-variant-numeric:tabular-nums}
#tip b{color:var(--text-primary);font-family:var(--mono);font-weight:500}

@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important}}
@media (max-width:640px){.wrap{padding:28px 14px 60px;gap:30px}.finding{padding:19px 16px}}
@media print{.kpi,.finding{box-shadow:none}}
"""

JS = """
(function(){
  var tip=document.getElementById('tip');
  if(!tip)return;
  document.addEventListener('mouseover',function(e){
    var t=e.target.closest('[data-tip]'); if(!t)return;
    tip.innerHTML=t.getAttribute('data-tip'); tip.style.opacity='1';
  });
  document.addEventListener('mousemove',function(e){
    if(tip.style.opacity!=='1')return;
    var r=tip.getBoundingClientRect();
    var x=e.clientX+14, y=e.clientY+14;
    if(x+r.width>window.innerWidth-8) x=e.clientX-r.width-14;
    if(y+r.height>window.innerHeight-8) y=e.clientY-r.height-14;
    tip.style.left=x+'px'; tip.style.top=y+'px';
  });
  document.addEventListener('mouseout',function(e){
    if(e.target.closest('[data-tip]')) tip.style.opacity='0';
  });
})();
"""
