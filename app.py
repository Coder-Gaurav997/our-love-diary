"""🌿 Avrav Love Diary — Supabase edition (rich features)."""
import io, pathlib, random, uuid
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
from PIL import Image

st.set_page_config(page_title="Our Love Diary", page_icon="❤️", layout="centered")

_share    = st.query_params.get("share") == "1"
_public   = st.query_params.get("public") == "1"
_readonly = _share or _public
_search   = st.query_params.get("q", "").strip()

try:
    SB_URL = st.secrets["SUPABASE_URL"]; SB_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    st.error("🔑 Supabase credentials missing."); st.stop()

BUCKET, TABLE = "moments-images", "moments"

@st.cache_resource
def _sb() -> Client: return create_client(SB_URL, SB_KEY)
supabase = _sb()

START, PWD = "2026-05-01", "gaurav&avni"
EMOJIS = ["💖","💌","🌙","☕","💗","✈️","💍","🌸","🎂","🎄","🌊","⭐","🎁","✨"]
DEFAULTS = {"title":"Untitled Moment","date":"—","emoji":"💖","about":"","images":[]}
AMBIENT = {
    "💖":("rgba(255,200,220,.35)","rgba(255,140,190,.20)"), "💌":("rgba(255,220,200,.35)","rgba(255,170,150,.20)"),
    "🌙":("rgba(200,215,255,.35)","rgba(150,170,240,.20)"), "☕":("rgba(220,200,175,.35)","rgba(180,150,120,.20)"),
    "💗":("rgba(255,190,215,.35)","rgba(255,120,175,.20)"), "✈️":("rgba(200,230,255,.35)","rgba(140,200,245,.20)"),
    "💍":("rgba(255,235,200,.35)","rgba(240,200,140,.20)"), "🌸":("rgba(255,210,225,.35)","rgba(255,160,200,.20)"),
    "🎂":("rgba(255,225,210,.35)","rgba(255,180,160,.20)"), "🎄":("rgba(200,240,210,.35)","rgba(150,220,170,.20)"),
    "🌊":("rgba(190,225,255,.35)","rgba(120,190,240,.20)"), "⭐":("rgba(255,240,200,.35)","rgba(245,215,140,.20)"),
    "🎁":("rgba(255,210,215,.35)","rgba(245,160,180,.20)"), "✨":("rgba(240,220,255,.35)","rgba(200,170,255,.20)")}
REASONS = [
    "The way your eyes light up when you talk about your dreams.",
    "How you remember tiny details I forgot I ever told you.",
    "The sound of your laugh on a bad day — my favourite medicine.",
    "The way you hum when you think no one is listening.",
    "How safe the world feels when you're next to me.",
    "The tiny crinkle at the corner of your eyes when you smile.",
    "How you always know exactly what I need before I do.",
    "The way you argue with me over the last bite — then give it to me anyway.",
    "How you text me just to say 'thinking of you' for no reason.",
    "The way you fall asleep mid-conversation — and I let you.",
    "How proud I feel walking into any room with you.",
    "The way you make ordinary days feel like tiny celebrations.",
    "Your terrible jokes that I secretly find hilarious.",
    "How you always send me songs that make you think of us.",
    "The way you hold my hand a little tighter when you're nervous."]

for k in ("show_add","unlocked","edit","del_mode"): st.session_state.setdefault(k, False)

# ── HELPERS ────────────────────────────────────────────────────────────────
def _compress(data, max_side=1920, quality=85):
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA","P"):
            bg = Image.new("RGB", img.size, (255,255,255))
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None); img = bg
        elif img.mode != "RGB": img = img.convert("RGB")
        w, h = img.size
        if max(w,h) > max_side:
            s = max_side/max(w,h); img = img.resize((int(w*s),int(h*s)), Image.LANCZOS)
        out = io.BytesIO(); img.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()
    except Exception: return data

def _load():
    try:
        rows = (supabase.table(TABLE).select("slug,title,date,emoji,about,images,created_at")
                .order("created_at").execute().data) or []
    except Exception as e:
        st.error(f"Could not load moments — {e}"); return {}
    return {(r.get("slug") or str(r.get("id"))):{
        "title":r.get("title") or "Untitled Moment","date":r.get("date") or "—",
        "emoji":r.get("emoji") or "💖","about":r.get("about") or "","images":r.get("images") or []} for r in rows}

def _key_for(title, existing):
    base = "".join(c if c.isalnum() else "_" for c in title.lower())[:40] or "moment"
    key, i = base, 1
    while key in existing: key, i = f"{base}_{i}", i+1
    return key

def _upload(f):
    name = f"{uuid.uuid4().hex}.jpg"
    try:
        raw = bytes(f.getbuffer())
        if (pathlib.Path(f.name).suffix.lower() or ".jpg")[:8] in (".jpg",".jpeg",".png",".webp"):
            raw = _compress(raw)
        supabase.storage.from_(BUCKET).upload(path=name, file=raw,
            file_options={"content-type":"image/jpeg","upsert":"true"})
        return supabase.storage.from_(BUCKET).get_public_url(name)
    except Exception as e: st.error(f"Upload failed — {e}"); return ""

def _rm(url):
    if not url or not url.startswith("http"): return
    try: supabase.storage.from_(BUCKET).remove([url.split(f"/{BUCKET}/")[-1].split("?")[0]])
    except Exception: pass

def add_moment(title, date, emoji, about, files):
    paths = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).insert({"slug":_key_for(title,_load()),"title":title.strip(),
            "date":date.strip(),"emoji":emoji,"about":about.strip(),"images":paths}).execute()
        return True
    except Exception as e: st.error(f"Could not save — {e}"); return False

def update_moment(slug, title, date, emoji, about, keep, files):
    for old in (MOMENTS.get(slug,{}).get("images") or []):
        if old not in keep: _rm(old)
    new = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).update({"title":title.strip(),"date":date.strip(),"emoji":emoji,
            "about":about.strip(),"images":list(keep)+new}).eq("slug",slug).execute()
    except Exception as e: st.error(f"Could not update — {e}")

def delete_moment(slug):
    for img in (MOMENTS.get(slug,{}).get("images") or []): _rm(img)
    try: supabase.table(TABLE).delete().eq("slug",slug).execute()
    except Exception as e: st.error(f"Could not delete — {e}")

def norm(m):
    out = dict(DEFAULTS); out.update({k:v for k,v in (m or {}).items() if v is not None})
    if not isinstance(out.get("images"), list):
        out["images"] = [out["images"]] if out.get("images") else []
    for f in ("title","date","emoji","about"): out[f] = (out.get(f) or DEFAULTS[f]).strip()
    return out

def imgs_of(m): return [p for p in norm(m)["images"] if p]

# ── PARTICLES ──────────────────────────────────────────────────────────────
rng = random.Random(42)
def _p(cls, n):
    return "".join(f'<span class="{cls}" style="left:{rng.uniform(0,100):.1f}%;'
        + (f'top:{rng.uniform(0,100):.1f}%;' if cls=="dot" else '')
        + f'--d:{rng.uniform(0,14):.1f}s;--t:{rng.uniform(8,15):.1f}s;'
        f'--s:{rng.uniform(2 if cls=="dot" else 9, 5 if cls=="dot" else 28):.1f}px;'
        f'--x:{rng.uniform(-90,90):.0f}px"></span>' for _ in range(n))

def _bokeh(n=4):
    return "".join(f'<span class="bokeh" style="left:{rng.uniform(0,100):.1f}%;'
        f'top:{rng.uniform(0,100):.1f}%;--bs:{rng.uniform(28,60):.0f}px;'
        f'--bd:{rng.uniform(0,8):.1f}s;--bt:{rng.uniform(6,11):.1f}s"></span>' for _ in range(n))

def _petals(n=10):
    return "".join(f'<span class="petal" style="left:{rng.uniform(0,100):.1f}%;'
        f'--d:{rng.uniform(0,20):.1f}s;--t:{rng.uniform(12,22):.1f}s;'
        f'--s:{rng.uniform(8,15):.1f}px;--x:{rng.uniform(-100,100):.0f}px"></span>' for _ in range(n))

PARTICLES = ('<div class="living-bg" id="living-bg"><div class="soft-glow"></div>'
    f'{_bokeh(4)}{_p("bubble",8)}{_p("leaf",6)}{_p("dot",14)}{_petals(10)}</div>')
LOADER_HTML = '<div class="avrav-loader" id="avrav-loader"><div class="ld-heart">💗</div><div class="ld-text">Loading our story…</div><div class="ld-bar"><div class="ld-bar-fill"></div></div></div>'

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&family=Cormorant+Garamond:ital,wght@1,800&family=Lora:ital,wght@1,700&family=Inter:wght@500;600;700&family=Dancing+Script:wght@700&display=swap');

  header[data-testid="stHeader"],[data-testid="manage-app-button"],
  #MainMenu,footer,.stDeployButton{display:none !important;visibility:hidden !important}
  :root{color-scheme:light only}
  .stApp{background:linear-gradient(110deg,#e07ba0 0%,#6fa8d4 100%);background-attachment:fixed}
  .block-container{padding-top:2rem;max-width:1080px;position:relative;z-index:3}

  .avrav-loader{position:fixed;inset:0;z-index:99999;background:linear-gradient(110deg,#e07ba0 0%,#6fa8d4 100%);
    display:flex;flex-direction:column;align-items:center;justify-content:center;transition:opacity .5s ease}
  .ld-heart{font-size:4rem;animation:ldbeat 1.2s ease-in-out infinite;filter:drop-shadow(0 6px 20px rgba(0,0,0,.3))}
  @keyframes ldbeat{0%,100%{transform:scale(1)}50%{transform:scale(1.2)}}
  .ld-text{font-family:'Dancing Script',cursive;font-weight:700;font-size:1.8rem;color:#fff;margin-top:14px;text-shadow:0 2px 12px rgba(0,0,0,.4)}
  .ld-bar{width:220px;height:4px;margin-top:22px;border-radius:999px;background:rgba(255,255,255,.25);overflow:hidden}
  .ld-bar-fill{height:100%;width:40%;border-radius:999px;background:#fff;animation:ldslide 1.4s ease-in-out infinite}
  @keyframes ldslide{0%{transform:translateX(-100%)}100%{transform:translateX(350%)}}

  .offline-banner{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(120px);
    background:linear-gradient(135deg,#3a020f 0%,#7a0a1e 100%);color:#fff;padding:12px 24px;border-radius:999px;
    font-family:'Inter',sans-serif;font-weight:700;font-size:.9rem;box-shadow:0 12px 34px rgba(0,0,0,.55);
    z-index:99998;display:flex;align-items:center;gap:10px;transition:transform .4s cubic-bezier(.2,.8,.2,1)}
  .offline-banner.show{transform:translateX(-50%) translateY(0)}
  .offline-dot{width:10px;height:10px;border-radius:50%;background:#ff4d6d;box-shadow:0 0 12px #ff4d6d;animation:pulse 1.4s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

  .to-top-heart{position:fixed;bottom:26px;right:26px;z-index:9999;width:58px;height:58px;border-radius:50%;
    background:linear-gradient(135deg,#c2185b 0%,#7a0a1e 100%);color:#fff;font-size:1.5rem;
    display:flex;align-items:center;justify-content:center;cursor:pointer;pointer-events:auto;border:3px solid #fff;
    box-shadow:0 10px 28px rgba(122,10,30,.55),0 0 20px rgba(194,24,91,.5);
    transition:transform .3s cubic-bezier(.2,.8,.2,1),opacity .3s ease;opacity:0;transform:translateY(20px) scale(.8)}
  .to-top-heart.show{opacity:1;transform:translateY(0) scale(1)}
  .to-top-heart:hover{transform:translateY(-4px) scale(1.08)}
  @media (max-width:680px){.to-top-heart{width:48px;height:48px;bottom:18px;right:18px;font-size:1.25rem}}

  .mini-map{position:fixed;top:50%;right:16px;transform:translateY(-50%);z-index:9997;
    display:flex;flex-direction:column;gap:8px;padding:12px 10px;border-radius:999px;
    background:rgba(255,255,255,.85);border:2px solid #0B2E1A;box-shadow:0 10px 26px rgba(11,46,26,.3);pointer-events:auto}
  .mini-map a{display:block;width:12px;height:12px;border-radius:50%;background:rgba(122,10,30,.35);transition:all .25s}
  .mini-map a:hover{background:#c2185b;transform:scale(1.5);box-shadow:0 0 10px rgba(194,24,91,.8)}
  @media (max-width:820px){.mini-map{display:none}}
  .search-hint{text-align:center;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;
    font-size:.95rem;color:#0B2E1A;margin-top:8px;opacity:.75}

  .living-bg{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:1;transform:translateZ(0);contain:strict}
  .soft-glow{position:absolute;top:-25%;right:-15%;width:65vmax;height:65vmax;border-radius:50%;
    background:radial-gradient(circle,rgba(255,170,215,.45) 0%,rgba(255,170,215,.25) 20%,rgba(180,200,255,.15) 45%,transparent 72%);
    opacity:.55;animation:softDrift 32s ease-in-out infinite;will-change:transform;transform:translateZ(0);pointer-events:none}
  @keyframes softDrift{0%,100%{transform:translate3d(0,0,0) scale(1)}50%{transform:translate3d(-4%,3%,0) scale(1.08)}}
  .bokeh{position:absolute;width:var(--bs);height:var(--bs);border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,.85) 0%,rgba(255,210,230,.4) 35%,transparent 70%);
    opacity:0;pointer-events:none;transform:translateZ(0);animation:bokehFloat var(--bt) ease-in-out var(--bd) infinite alternate}
  @keyframes bokehFloat{0%{opacity:.3;transform:translate3d(0,0,0) scale(1)}100%{opacity:.7;transform:translate3d(15px,-25px,0) scale(1.2)}}
  .bubble{position:absolute;bottom:-50px;width:var(--s);height:var(--s);border-radius:50%;
    background:radial-gradient(circle at 30% 28%,rgba(255,255,255,.95) 0%,rgba(255,255,255,.35) 28%,rgba(180,220,255,.20) 55%,rgba(255,255,255,.05) 100%);
    border:1px solid rgba(255,255,255,.55);
    box-shadow:inset -2px -3px 6px rgba(255,255,255,.55),inset 2px 2px 4px rgba(120,180,240,.35),0 0 10px rgba(255,255,255,.45);
    animation:rise var(--t) linear var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes rise{0%{transform:translate3d(0,0,0) scale(.5);opacity:0}10%{opacity:.95}
    50%{transform:translate3d(calc(var(--x)*.6),-50vh,0) scale(1);opacity:.85}90%{opacity:.55}
    100%{transform:translate3d(var(--x),-110vh,0) scale(1.15);opacity:0}}
  .leaf{position:absolute;top:-50px;width:var(--s);height:calc(var(--s)*.6);
    background:linear-gradient(135deg,#a4e07a 0%,#4caf50 55%,#2e7d32 100%);border-radius:50% 0 50% 0;
    box-shadow:inset -1px -1px 3px rgba(0,0,0,.2),inset 1px 1px 2px rgba(255,255,255,.35),0 3px 6px rgba(0,0,0,.15);
    animation:fall-leaf var(--t) linear var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes fall-leaf{0%{transform:translate3d(0,-10vh,0) rotate(0) rotateY(0);opacity:0}8%{opacity:.9}
    50%{transform:translate3d(calc(var(--x)*.5),50vh,0) rotate(360deg) rotateY(180deg)}90%{opacity:.75}
    100%{transform:translate3d(var(--x),115vh,0) rotate(720deg) rotateY(360deg);opacity:0}}
  .petal{position:absolute;top:-40px;width:var(--s);height:calc(var(--s)*.7);
    background:radial-gradient(circle at 40% 30%,#ffd0e5 0%,#ff9ec2 45%,#e56a9a 100%);border-radius:60% 5% 60% 5%;
    box-shadow:inset -1px -1px 2px rgba(180,60,110,.25),inset 1px 1px 2px rgba(255,255,255,.6),0 2px 5px rgba(180,60,110,.18);
    animation:petalFall var(--t) linear var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes petalFall{0%{transform:translate3d(0,-10vh,0) rotate(0) rotateY(0);opacity:0}8%{opacity:.85}
    50%{transform:translate3d(calc(var(--x)*.5),50vh,0) rotate(270deg) rotateY(180deg);opacity:.75}90%{opacity:.6}
    100%{transform:translate3d(var(--x),115vh,0) rotate(540deg) rotateY(360deg);opacity:0}}
  .dot{position:absolute;width:var(--s);height:var(--s);border-radius:50%;background:#fff;
    box-shadow:0 0 5px rgba(255,255,255,.95),0 0 12px rgba(255,246,200,.85),0 0 22px rgba(255,240,180,.55);
    animation:twinkle var(--t) ease-in-out var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes twinkle{0%,100%{opacity:0;transform:scale(.4)}50%{opacity:1;transform:scale(1.35)}}

  @keyframes fadeInDown{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:none}}
  @keyframes fadeInUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
  @keyframes beat{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
  @keyframes fadeInOut{0%,100%{opacity:.6}50%{opacity:1}}
  @keyframes lovePulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
  @keyframes confettiFloat{0%{opacity:1;transform:translate(-50%,-50%) scale(.8)}
    100%{opacity:0;transform:translate(calc(-50% + var(--dx)),calc(-50% + var(--dy))) scale(1.4) rotate(15deg)}}

  h1.love-title{font-family:'Great Vibes',cursive !important;text-align:center;font-size:5.5rem;font-weight:600;
    color:#0B2E1A;margin:0;-webkit-text-stroke:3.5px #fff;paint-order:stroke fill;
    text-shadow:0 2px 0 rgba(255,255,255,.9),0 4px 16px rgba(11,46,26,.5),0 0 20px rgba(255,255,255,.9),0 0 36px rgba(255,255,255,.5);
    animation:fadeInDown 1s cubic-bezier(.2,.8,.2,1) both}
  p.love-sub{font-family:'Cormorant Garamond',serif !important;font-weight:800;font-style:italic;text-align:center;
    font-size:1.15rem;letter-spacing:.35em;text-transform:uppercase;color:#0B2E1A;margin:.9rem auto 0 auto;
    display:inline-block;padding:.5rem 1.5rem;border:2px solid #7a0a1e;border-radius:999px;background:rgba(255,255,255,.88);
    box-shadow:0 8px 22px rgba(11,46,26,.3),0 0 12px rgba(255,214,232,.9);
    animation:fadeInUp .9s .15s cubic-bezier(.2,.8,.2,1) both}

  .timeline{position:relative;max-width:920px;margin:10px auto 30px auto;padding:30px 0;contain:layout paint style}
  .timeline::before{content:'';position:absolute;left:50%;top:0;bottom:0;width:4px;transform:translateX(-50%);border-radius:4px;
    background:linear-gradient(180deg,transparent 0%,#0B2E1A 8%,#c2185b 50%,#0B2E1A 92%,transparent 100%)}
  .tl-item{position:relative;width:50%;padding:20px 60px;box-sizing:border-box;opacity:0;transform:translateY(28px);
    animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:var(--d);scroll-margin-top:80px}
  .tl-item.left{left:0;text-align:right}.tl-item.right{left:50%;text-align:left}
  .tl-heart{position:absolute;top:28px;width:36px;height:36px;z-index:3;
    filter:drop-shadow(0 3px 8px rgba(11,46,26,.5));animation:beat 2.4s ease-in-out infinite}
  .tl-item.left .tl-heart{right:-18px}.tl-item.right .tl-heart{left:-18px}
  .tl-heart svg{width:100%;height:100%}
  a.tl-card,a.tl-card:visited,a.tl-card:hover,a.tl-card:active{text-decoration:none;color:inherit}
  .tl-card{display:inline-block;padding:18px 26px;border-radius:18px;background:rgba(255,255,255,.94);
    border:2px solid #0B2E1A;box-shadow:0 10px 28px rgba(11,46,26,.32);
    transition:transform .3s cubic-bezier(.2,.8,.2,1),box-shadow .3s ease,border-color .3s ease,background .3s ease;
    text-align:inherit;position:relative;overflow:hidden;cursor:pointer;min-width:240px;min-height:96px;transform-style:preserve-3d}
  .tl-card:hover{transform:translateY(-5px) scale(1.03);background:#fff;border-color:#7a0a1e;box-shadow:0 20px 44px rgba(11,46,26,.5)}
  .tl-content{display:block;transition:opacity .25s ease}
  .tl-card:hover .tl-content{opacity:0}
  .tl-hover-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Lora',serif;
    font-style:italic;font-weight:700;font-size:1.55rem;color:#7a0a1e;-webkit-text-stroke:.6px #7a0a1e;opacity:0;transform:scale(.94);
    transition:opacity .25s ease,transform .25s ease;pointer-events:none;text-align:center;padding:0 12px}
  .tl-card:hover .tl-hover-text{opacity:1;transform:scale(1)}
  .tl-emoji{display:inline-block;font-size:1.25rem;margin-bottom:4px}
  .tl-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.55rem;color:#04160C;line-height:1.25;
    margin:2px 0 8px 0;-webkit-text-stroke:.5px #04160C}
  .tl-date{display:inline-block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;font-size:.9rem;
    letter-spacing:.22em;text-transform:uppercase;color:#4a0312;padding:4px 14px;border-radius:999px;background:#ffd9e8;border:2px solid #7a0a1e}

  .empty-state,.no-photo,.ending-card,.add-panel,.danger-box,.detail-about{
    background:rgba(255,255,255,.94);border:2px solid #0B2E1A;box-shadow:0 12px 32px rgba(11,46,26,.3)}
  .empty-state{max-width:640px;margin:40px auto;padding:50px 40px;border-radius:24px;text-align:center;
    animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) both}
  .empty-emoji{font-size:3rem;display:block;margin-bottom:12px}
  .empty-title{font-family:'Great Vibes',cursive;font-size:2.5rem;color:#04160C;margin:0 0 10px 0}
  .empty-text{font-family:'Lora',serif;font-style:italic;font-size:1.08rem;color:#04160C;line-height:1.7}
  .empty-hint{display:inline-block;margin-top:16px;font-family:'Inter',sans-serif;font-weight:700;font-size:.85rem;
    letter-spacing:.14em;text-transform:uppercase;color:#fff;padding:9px 20px;border-radius:999px;
    background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%);border:2px solid #062b18;box-shadow:0 6px 18px rgba(6,43,24,.4)}
  .no-photo{max-width:820px;margin:24px auto 22px auto;padding:56px 30px;border-radius:20px;text-align:center;border-style:dashed}
  .no-photo-emoji{font-size:3rem;display:block;margin-bottom:10px}
  .no-photo-text{font-family:'Lora',serif;font-style:italic;font-size:1.1rem;color:#04160C}

  .ending-card{max-width:720px;margin:30px auto 20px auto;padding:34px 40px;border-radius:24px;text-align:center;
    position:relative;overflow:hidden;border-style:dashed;animation:fadeInUp 1s .6s cubic-bezier(.2,.8,.2,1) both}
  .ending-heart{font-size:2.3rem;display:block;margin-bottom:8px;animation:beat 2.4s ease-in-out infinite}
  .ending-title{font-family:'Great Vibes',cursive;font-size:2.7rem;color:#04160C;margin:4px 0 10px 0;text-shadow:0 2px 10px rgba(194,24,91,.35)}
  .ending-text{font-family:'Lora',serif;font-style:italic;font-weight:500;font-size:1.1rem;color:#04160C;line-height:1.75}
  .ending-dots{margin-top:16px;letter-spacing:1em;font-size:1.5rem;color:#c2185b;animation:fadeInOut 2.6s ease-in-out infinite}

  /* ═══ REASONS ═══ */
  .reasons-wrap{max-width:920px;margin:20px auto 6px auto;padding:28px 24px 22px 24px;border-radius:24px;
    position:relative;overflow:hidden;
    background:linear-gradient(135deg,#fbe3cd 0%,#f8dcc0 55%,#f5d3b3 100%);
    border:2px solid #0B2E1A;box-shadow:0 14px 36px rgba(11,46,26,.35),inset 0 1px 0 rgba(255,255,255,.7);
    animation:fadeInUp 1s .7s cubic-bezier(.2,.8,.2,1) both}
  .reasons-head,[data-testid="stMarkdownContainer"] .reasons-head,
  [data-testid="stMarkdownContainer"] h2.reasons-head,h2.reasons-head{
    font-family:'Dancing Script',cursive !important;font-style:normal !important;font-weight:700 !important;
    font-size:3.4rem !important;color:#0a0704 !important;-webkit-text-fill-color:#0a0704 !important;
    text-align:center !important;margin:0 0 24px 0 !important;line-height:1.15 !important;letter-spacing:.01em !important;
    -webkit-text-stroke:0 !important;text-shadow:0 2px 8px rgba(122,10,30,.35),0 1px 0 rgba(255,255,255,.5) !important;
    display:block !important;width:100% !important}
  .reasons-track{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;gap:16px;
    padding:6px 4px 14px 4px;-ms-overflow-style:none;scrollbar-width:none}
  .reasons-track::-webkit-scrollbar{display:none}
  .reason-card{flex:0 0 82%;max-width:82%;scroll-snap-align:center;padding:22px 26px;border-radius:20px;
    background:linear-gradient(135deg,#fff4e8 0%,#fbe1c8 100%);border:2px solid #7a0a1e;
    box-shadow:0 10px 26px rgba(122,10,30,.25),inset 0 1px 0 rgba(255,255,255,.85);
    font-family:'Lora',serif;font-style:italic;font-weight:600;font-size:1.15rem;line-height:1.65;color:#3a020f;text-align:center}
  .reason-card .rnum{display:block;font-family:'Cormorant Garamond',serif;font-weight:800;font-size:.72rem;
    letter-spacing:.3em;color:#c2185b;text-transform:uppercase;margin-bottom:10px;opacity:.85}
  .reasons-nav{display:flex;justify-content:center;align-items:center;gap:14px;margin-top:8px}
  .reasons-btn{background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%);border:2px solid #062b18;color:#fff;
    width:46px;height:46px;border-radius:50%;font-size:1.2rem;font-weight:700;cursor:pointer;
    box-shadow:0 6px 16px rgba(6,43,24,.5);transition:transform .2s ease,box-shadow .2s ease;
    display:flex;align-items:center;justify-content:center;padding:0;line-height:1}
  .reasons-btn:hover{transform:translateY(-2px) scale(1.08);box-shadow:0 10px 24px rgba(6,43,24,.7)}
  .reasons-btn:active{transform:scale(.94)}
  .reasons-count{font-family:'Inter',sans-serif;font-weight:700;font-size:.82rem;color:#3a020f;letter-spacing:.1em;min-width:56px;text-align:center}

  .detail-wrap{max-width:880px;margin:10px auto 40px auto;position:relative;animation:fadeInUp .8s cubic-bezier(.2,.8,.2,1) both}
  .detail-ambient{position:absolute;inset:-40px -20px;border-radius:40px;pointer-events:none;z-index:-1;filter:blur(30px);opacity:.65}
  .detail-hero{text-align:center;margin:10px 0 18px 0;position:relative;z-index:1}
  .detail-emoji{font-size:3.5rem;display:block;margin-bottom:6px;filter:drop-shadow(0 4px 12px rgba(11,46,26,.5))}
  .detail-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:2.8rem;color:#04160C;margin:6px 0 12px 0;
    line-height:1.15;text-shadow:0 2px 12px rgba(255,255,255,.9)}
  .detail-date{display:inline-block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;font-size:1rem;
    letter-spacing:.28em;text-transform:uppercase;color:#4a0312;padding:6px 20px;border-radius:999px;background:#ffd9e8;
    border:2px solid #7a0a1e;box-shadow:0 6px 18px rgba(122,10,30,.3)}
  .gallery{display:grid;gap:14px;margin:24px auto 22px auto;max-width:820px;position:relative;z-index:1;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
  .gallery img{width:100%;height:220px;object-fit:cover;border-radius:18px;border:3px solid #0B2E1A;
    box-shadow:0 14px 32px rgba(11,46,26,.5);transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease;
    cursor:pointer;filter:contrast(1.05) saturate(1.05)}
  .gallery img:hover{transform:translateY(-6px) scale(1.03);box-shadow:0 22px 48px rgba(11,46,26,.65)}
  .gallery img.single{grid-column:1/-1;height:auto;max-height:520px}
  .detail-about{max-width:820px;margin:0 auto;padding:28px 32px;border-radius:20px;font-family:'Lora',serif;
    font-style:italic;font-weight:500;font-size:1.2rem;line-height:1.85;color:#04160C;position:relative;overflow:hidden;z-index:1}
  .detail-label{display:block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:800;font-size:.85rem;
    letter-spacing:.28em;text-transform:uppercase;color:#7a0a1e;margin-bottom:8px}
  .detail-empty-story{opacity:.7;font-style:italic}

  .stButton>button{background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%);border:2px solid #062b18;color:#fff;
    font-family:'Inter',sans-serif;font-weight:700;letter-spacing:.04em;border-radius:999px;white-space:nowrap;
    text-shadow:0 1px 3px rgba(0,0,0,.55);box-shadow:0 8px 22px rgba(6,43,24,.5),inset 0 1px 2px rgba(255,255,255,.3);
    transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s ease,background .25s ease}
  .stButton>button:hover{background:linear-gradient(135deg,#14532d 0%,#237a4a 55%,#3ab877 100%);border-color:#0d3b25;
    transform:translateY(-2px) scale(1.03);box-shadow:0 14px 32px rgba(6,43,24,.7),inset 0 1px 3px rgba(255,255,255,.5)}
  .stButton>button:active{transform:translateY(0) scale(.97)}
  .stButton>button p{color:#fff !important;font-weight:700 !important}
  .stButton>button[kind="secondary"]{padding:.42rem 1.1rem;font-size:.88rem}
  .stButton>button[kind="primary"]{background:linear-gradient(135deg,#5b0616 0%,#7a0a1e 45%,#c2185b 100%);
    border-color:#3a030e;padding:.42rem 1.1rem;font-size:.88rem}
  .stButton>button[kind="primary"]:hover{background:linear-gradient(135deg,#7a0a1e 0%,#a10a4a 45%,#e02a72 100%);border-color:#5b0616}

  .stTextInput input,.stTextArea textarea,.stDateInput input{
    background:#fff5f9 !important;color:#3a020f !important;border-radius:14px !important;border:2px solid #7a0a1e !important;
    font-family:'Lora',serif !important;font-weight:600 !important;font-size:1.02rem !important;
    box-shadow:inset 0 2px 6px rgba(122,10,30,.12) !important;transition:all .25s ease !important}
  .stTextInput input:focus,.stTextArea textarea:focus,.stDateInput input:focus{
    border-color:#c2185b !important;background:#fff !important;
    box-shadow:0 0 0 3px rgba(194,24,91,.28),inset 0 2px 6px rgba(122,10,30,.12) !important}
  .stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#8a4a60 !important;font-style:italic !important}
  .stTextInput label,.stTextArea label,.stDateInput label,.stSelectbox label,.stFileUploader label,.stMultiSelect label{
    color:#0B2E1A !important;font-family:'Cormorant Garamond',serif !important;font-style:italic !important;
    font-weight:800 !important;letter-spacing:.15em !important;font-size:1.12rem !important}
  .stSelectbox div[data-baseweb="select"]>div,.stMultiSelect div[data-baseweb="select"]>div{
    background:#fff5f9 !important;border:2px solid #7a0a1e !important;border-radius:14px !important;
    color:#3a020f !important;font-family:'Lora',serif !important;font-weight:600 !important}
  .stFileUploader section{background:#fff5f9 !important;border:2px dashed #7a0a1e !important;border-radius:16px !important;
    transition:all .25s ease !important}
  .stFileUploader section:hover{border-color:#c2185b !important}
  section[data-testid="stFileUploadDropzone"]{color:#3a020f !important}
  section[data-testid="stFileUploadDropzone"] button{
    background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%) !important;color:#fff !important;
    border:2px solid #062b18 !important;border-radius:999px !important;font-family:'Inter',sans-serif !important;font-weight:700 !important}

  .add-panel{max-width:720px;margin:10px auto 30px auto;padding:28px 32px;border-radius:22px;
    animation:fadeInUp .7s cubic-bezier(.2,.8,.2,1) both}
  .add-title,.add-panel h2,h2.add-title,[data-testid="stMarkdownContainer"] h2.add-title,
  [data-testid="stMarkdownContainer"] .add-panel h2{
    font-family:'Great Vibes',cursive !important;font-size:2.7rem !important;font-weight:600 !important;
    text-align:center !important;margin:0 0 8px 0 !important;color:#04160C !important;
    -webkit-text-fill-color:#04160C !important;-webkit-text-stroke:0 !important;opacity:1 !important}
  .danger-box{max-width:720px;margin:16px auto;padding:24px 28px;border-radius:18px;text-align:center;border-style:dashed;
    background:#fff5f8;animation:fadeInUp .5s ease-out both}
  .danger-title{font-family:'Lora',serif;font-style:italic;font-weight:800;font-size:1.4rem;color:#7a0a1e;margin:0 0 8px 0}
  .danger-text{font-family:'Lora',serif;font-style:italic;color:#3a020f;font-size:1rem}

  .love-note{max-width:720px;margin:24px auto 70px auto;padding:30px 20px;text-align:center;
    animation:fadeInUp 1.2s .9s cubic-bezier(.2,.8,.2,1) both}
  .love-note-line{width:170px;height:2px;margin:0 auto;background:linear-gradient(90deg,transparent,#0B2E1A 40%,#0B2E1A 60%,transparent);
    border-radius:2px;opacity:.85}
  .love-note-text{font-family:'Dancing Script',cursive;font-weight:700;font-size:4.4rem;color:#c2185b;margin:14px 0 8px 0;line-height:1.15;
    text-shadow:0 0 14px rgba(255,92,138,.7),0 3px 14px rgba(122,10,30,.6),0 2px 0 #fff;
    -webkit-text-stroke:1.6px #fff;paint-order:stroke fill;animation:lovePulse 3s ease-in-out infinite}
  .love-note-sub{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:800;font-size:1.15rem;
    letter-spacing:.35em;text-transform:uppercase;color:#0B2E1A;margin:0 0 18px 0}

  @media (max-width:680px){
    .timeline::before{left:22px}
    .tl-item{width:100%;left:0 !important;text-align:left !important;padding:18px 20px 18px 62px}
    .tl-item.left .tl-heart,.tl-item.right .tl-heart{left:5px;right:auto}
    .detail-title{font-size:2.05rem}.detail-about{font-size:1.08rem;padding:22px 24px}
    .tl-hover-text{font-size:1.3rem}.gallery{grid-template-columns:1fr}
    h1.love-title{font-size:3.6rem;-webkit-text-stroke:3px #fff}
    .love-note-text{font-size:2.9rem}.love-note-sub{font-size:.95rem;letter-spacing:.25em}
    .add-title,[data-testid="stMarkdownContainer"] h2.add-title{font-size:2.1rem !important}
    .reason-card{flex:0 0 92%;max-width:92%;font-size:1.02rem;padding:18px 20px}
    .reasons-head,[data-testid="stMarkdownContainer"] h2.reasons-head{font-size:2.6rem !important}}
  @media (prefers-reduced-motion: reduce){
    .soft-glow,.bokeh,.bubble,.leaf,.petal,.dot,.tl-heart,.ending-heart,.ending-dots,
    .love-note-text,.ld-heart,.ld-bar-fill{animation:none !important}}
</style>
""", unsafe_allow_html=True)

_loader = st.empty(); _loader.markdown(LOADER_HTML, unsafe_allow_html=True)
MOMENTS = _load()
_loader.empty()

st.markdown(PARTICLES, unsafe_allow_html=True)

components.html("""<script>
(function(){
  const p = window.parent.document;
  let heart = p.getElementById('to-top-heart');
  if (!heart) {
    heart = p.createElement('div'); heart.id='to-top-heart'; heart.className='to-top-heart';
    heart.innerHTML='❤️'; heart.title='Back to top';
    heart.onclick = () => window.parent.scrollTo({top:0,behavior:'smooth'});
    p.body.appendChild(heart);
  }
  function toggleHeart(){
    const y = p.documentElement.scrollTop || p.body.scrollTop || 0;
    heart.classList.toggle('show', y > 400);
  }
  p.addEventListener('scroll', toggleHeart, {passive:true}); toggleHeart();

  try {
    const svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#e07ba0"/><stop offset="100%" stop-color="#6fa8d4"/>
      </linearGradient></defs>
      <rect width="512" height="512" rx="96" fill="url(#g)"/>
      <path d="M256 400 C120 300 80 220 80 160 C80 110 120 70 170 70 C210 70 240 95 256 135 C272 95 302 70 342 70 C392 70 432 110 432 160 C432 220 392 300 256 400 Z"
            fill="#fff" stroke="#0B2E1A" stroke-width="14"/></svg>`;
    const iconData = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgIcon);
    const manifest = {name:"Our Love Diary",short_name:"Love Diary",start_url:".",scope:".",display:"standalone",
      orientation:"portrait",background_color:"#e07ba0",theme_color:"#e07ba0",
      description:"A little garden of our favourite moments",
      icons:[{src:iconData,sizes:"192x192",type:"image/svg+xml",purpose:"any maskable"},
             {src:iconData,sizes:"512x512",type:"image/svg+xml",purpose:"any maskable"}]};
    const mLink = p.createElement('link'); mLink.rel='manifest';
    mLink.href='data:application/manifest+json;charset=utf-8,' + encodeURIComponent(JSON.stringify(manifest));
    p.head.appendChild(mLink);
    ['theme-color:#e07ba0','apple-mobile-web-app-capable:yes','apple-mobile-web-app-status-bar-style:default'].forEach(pair => {
      const [name, content] = pair.split(':'); const m = p.createElement('meta');
      m.name = name; m.content = content; p.head.appendChild(m);
    });
    const apple = p.createElement('link'); apple.rel='apple-touch-icon'; apple.href=iconData; p.head.appendChild(apple);
  } catch(e) {}

  let banner = p.getElementById('offline-banner');
  if (!banner) {
    banner = p.createElement('div'); banner.id='offline-banner'; banner.className='offline-banner';
    banner.innerHTML='<span class="offline-dot"></span> You\\'re offline — will retry when back';
    p.body.appendChild(banner);
  }
  function updateOnline(){ banner.classList.toggle('show', !navigator.onLine); }
  window.parent.addEventListener('online', updateOnline);
  window.parent.addEventListener('offline', updateOnline);
  updateOnline();

  const bg = p.getElementById('living-bg');
  if (bg) {
    let r = false;
    p.addEventListener('scroll', () => {
      if (r) return; r = true;
      requestAnimationFrame(() => {
        const y = p.documentElement.scrollTop || p.body.scrollTop || 0;
        bg.style.transform = 'translate3d(0,' + (y*0.3) + 'px,0)'; r = false;
      });
    }, {passive:true});
  }

  if (!matchMedia('(hover: none)').matches) {
    let c = null, rect = null, mx = 0, my = 0, busy = false;
    p.addEventListener('mouseover', e => {
      const t = e.target.closest && e.target.closest('.tl-card');
      if (t && t !== c) { c = t; rect = t.getBoundingClientRect(); }
    }, {passive:true});
    p.addEventListener('mouseout', e => {
      const t = e.target.closest && e.target.closest('.tl-card');
      if (t && t === c) { t.style.transform = ''; c = null; rect = null; }
    }, {passive:true});
    p.addEventListener('mousemove', e => {
      if (!c) return; mx = e.clientX; my = e.clientY;
      if (busy) return; busy = true;
      requestAnimationFrame(() => {
        busy = false; if (!c || !rect) return;
        const x = (mx-rect.left)/rect.width - 0.5, y = (my-rect.top)/rect.height - 0.5;
        c.style.transform = 'perspective(700px) rotateY(' + (x*6) + 'deg) rotateX(' + (-y*6) + 'deg) translateY(-5px) scale(1.02)';
      });
    }, {passive:true});
  }

  let last = 0;
  p.addEventListener('click', e => {
    const t = e.target;
    if (t.closest('button,input,textarea,select,[data-testid="stFileUploaderDropzone"],a[download],.to-top-heart,.reasons-btn')) return;
    const now = Date.now(); if (now-last < 150) return; last = now;
    const g = ['❤️','💖','💕','💗','💘','🌸'];
    for (let i = 0; i < 3; i++) {
      const h = p.createElement('span');
      h.textContent = g[Math.floor(Math.random()*g.length)];
      h.style.cssText = 'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;font-size:' +
        (14+Math.random()*10) + 'px;pointer-events:none;z-index:99999;animation:confettiFloat ' +
        (0.9+Math.random()*0.6) + 's ease-out forwards;transform:translate(-50%,-50%);will-change:transform,opacity;';
      h.style.setProperty('--dx', (Math.random()-0.5)*180 + 'px');
      h.style.setProperty('--dy', -(60+Math.random()*100) + 'px');
      p.body.appendChild(h); setTimeout(() => h.remove(), 1600);
    }
  }, {passive:true});

    function attachReasons() {
    const track = p.getElementById('reasonsTrack');
    const prev  = p.getElementById('reasonsPrev');
    const next  = p.getElementById('reasonsNext');
    if (!track || !prev || !next) return false;
    if (prev.dataset.bound === '1') return true;   /* already bound */
    prev.dataset.bound = '1';
    next.dataset.bound = '1';
    const step = () => Math.max(track.clientWidth * 0.84, 240);
    prev.addEventListener('click', e => {
      e.preventDefault(); e.stopPropagation();
      track.scrollBy({ left: -step(), behavior: 'smooth' });
    });
    next.addEventListener('click', e => {
      e.preventDefault(); e.stopPropagation();
      track.scrollBy({ left:  step(), behavior: 'smooth' });
    });
    return true;
  }

  /* Attach now if already in DOM, then keep watching for Streamlit renders */
  attachReasons();
  const observer = new MutationObserver(() => attachReasons());
  observer.observe(p.body, { childList: true, subtree: true });

  window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:0}, '*');
})();
</script>""", height=0)

# ── Top bar ────────────────────────────────────────────────────────────────
if not _readonly:
    c1, c2 = st.columns([6, 4])
    with c1:
        if st.button("🎲 Surprise me", key="rand_btn", use_container_width=True):
            if MOMENTS:
                st.query_params["m"] = random.choice(list(MOMENTS.keys())); st.rerun()
    with c2:
        if st.button("✚ Add Moment", key="add_btn", use_container_width=True):
            st.session_state.show_add = True; st.session_state.edit = st.session_state.del_mode = False
            st.query_params.clear(); st.rerun()

st.markdown('<h1 class="love-title">Our Love Diary</h1>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center"><p class="love-sub">A Little Garden Of Our Favourite Moments!!</p></div>', unsafe_allow_html=True)

components.html(f"""<style>
  body{{margin:0;background:transparent}}
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap');
  .counter-wrap{{display:flex;justify-content:center;padding:20px 0 6px 0;animation:fadeInUp 1s .3s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes fadeInUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:none}}}}
  .days-counter{{display:inline-flex;align-items:center;gap:14px;padding:14px 28px;border-radius:999px;
    background:rgba(255,255,255,.94);border:2px solid #0B2E1A;box-shadow:0 12px 34px rgba(11,46,26,.35);
    font-family:'Inter',sans-serif;color:#04160C}}
  .counter-label{{font-weight:700;font-size:.85rem;letter-spacing:.22em;text-transform:uppercase;color:#04160C}}
  .counter-sep{{width:2px;height:28px;background:linear-gradient(180deg,transparent,rgba(11,46,26,.75),transparent)}}
  .counter-unit{{display:inline-flex;align-items:baseline;gap:5px}}
  .counter-unit b{{font-size:1.55rem;font-weight:700;color:#04160C;line-height:1;font-variant-numeric:tabular-nums;min-width:2.6ch;text-align:right}}
  .counter-unit span{{font-size:.75rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#04160C;opacity:.85}}
  @media(max-width:680px){{.days-counter{{gap:10px;padding:12px 18px}}
    .counter-unit b{{font-size:1.18rem}}.counter-unit span{{font-size:.68rem}}.counter-label{{font-size:.72rem}}}}
</style>
<div class="counter-wrap"><div class="days-counter">
  <span class="counter-label">Together</span><span class="counter-sep"></span>
  <span class="counter-unit"><b id="d">0</b><span>days</span></span><span class="counter-sep"></span>
  <span class="counter-unit"><b id="h">0</b><span>hrs</span></span><span class="counter-sep"></span>
  <span class="counter-unit"><b id="m">0</b><span>min</span></span><span class="counter-sep"></span>
  <span class="counter-unit"><b id="s">0</b><span>sec</span></span>
</div></div>
<script>
  const start=new Date("{START}T00:00:00"),pad=n=>String(n).padStart(2,'0');
  function tick(){{const diff=new Date()-start;
    document.getElementById('d').textContent=Math.floor(diff/86400000);
    document.getElementById('h').textContent=pad(Math.floor((diff%86400000)/3600000));
    document.getElementById('m').textContent=pad(Math.floor((diff%3600000)/60000));
    document.getElementById('s').textContent=pad(Math.floor((diff%60000)/1000));}}
  tick();setInterval(tick,1000);
</script>""", height=110)

st.markdown('<hr style="border:none;height:2.5px;width:90%;margin:1rem auto;background:linear-gradient(90deg,transparent,#0B2E1A 15%,#0B2E1A 85%,transparent);border-radius:2px;opacity:.85">', unsafe_allow_html=True)

active = st.query_params.get("m")
HEART = ('M16 28 C4 18 2 12 2 8 C2 4 5 1 9 1 C12 1 15 3 16 6 C17 3 20 1 23 1 C27 1 30 4 30 8 C30 12 28 18 16 28 Z')

# ═══ 1) ADD MOMENT ═════════════════════════════════════════════════════════
if st.session_state.show_add and not _readonly:
    if st.button("← Back to diary", key="back_add"):
        st.session_state.show_add = st.session_state.unlocked = False; st.rerun()
    if not st.session_state.unlocked:
        st.markdown('<div class="add-panel"><h2 class="add-title">🔒 Unlock the Diary</h2></div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", key="pwd_add")
        if st.button("Unlock ✨", key="unlock_add"):
            if pwd == PWD: st.session_state.unlocked = True; st.rerun()
            else: st.error("Wrong password — try again 💔")
    else:
        st.markdown('<div class="add-panel"><h2 class="add-title">✚ Add a New Moment</h2></div>', unsafe_allow_html=True)
        with st.form("add_form"):
            c1, c2 = st.columns([2, 1])
            title = c1.text_input("Title", placeholder="e.g. The First Snow")
            emoji = c2.selectbox("Emoji", EMOJIS)
            dv = st.date_input("Date", value=datetime.now())
            about = st.text_area("Our Story", height=160, placeholder="Write everything you remember…")
            files = st.file_uploader("Photos (auto-compressed)", accept_multiple_files=True, type=["png","jpg","jpeg","webp","gif"])
            if st.form_submit_button("Save Moment 💾"):
                if not title.strip(): st.warning("Please enter a title.")
                elif add_moment(title, dv.strftime("%d %b %Y"), emoji, about, files or []):
                    st.success(f"Saved “{title}” 💖")
                    st.session_state.show_add = st.session_state.unlocked = False; st.rerun()
                else: st.warning("Couldn't save — you may be offline.")

# ═══ 2) DETAIL PAGE ════════════════════════════════════════════════════════
elif active and active in MOMENTS:
    m = norm(MOMENTS[active])
    slugs = list(MOMENTS.keys()); idx = slugs.index(active)
    prev_slug = slugs[idx-1] if idx > 0 else None
    next_slug = slugs[idx+1] if idx < len(slugs)-1 else None

    if _readonly:
        c1, c2, c3 = st.columns([2, 1, 2])
        with c1:
            if prev_slug and st.button("← Previous", key="prev_top", use_container_width=True):
                st.query_params["m"] = prev_slug; st.rerun()
        with c2:
            if st.button("⌂ Home", key="home_top", use_container_width=True):
                st.query_params.clear(); st.rerun()
        with c3:
            if next_slug and st.button("Next →", key="next_top", use_container_width=True):
                st.query_params["m"] = next_slug; st.rerun()
    else:
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 3, 1.2, 1.2])
        with c1:
            if prev_slug and st.button("←", key="prev_top", use_container_width=True, help="Previous moment"):
                st.query_params["m"] = prev_slug; st.rerun()
        with c2:
            if next_slug and st.button("→", key="next_top", use_container_width=True, help="Next moment"):
                st.query_params["m"] = next_slug; st.rerun()
        with c4:
            if st.button("✏️ Edit", key="edit_b", use_container_width=True):
                st.session_state.edit = True; st.session_state.del_mode = False; st.session_state.unlocked = False; st.rerun()
        with c5:
            if st.button("🗑️ Delete", key="del_b", use_container_width=True, type="primary"):
                st.session_state.del_mode = True; st.session_state.edit = False; st.session_state.unlocked = False; st.rerun()
        with c3:
            if st.button("← Back to timeline", key="back_d", use_container_width=True):
                st.query_params.clear(); st.session_state.edit = st.session_state.del_mode = False; st.rerun()

    if not _readonly and (st.session_state.edit or st.session_state.del_mode) and not st.session_state.unlocked:
        st.markdown('<div class="add-panel"><h2 class="add-title">🔒 Unlock to continue</h2></div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", key="pwd_ed")
        c1, c2 = st.columns(2)
        if c1.button("Unlock ✨", key="unlock_ed", use_container_width=True):
            if pwd == PWD: st.session_state.unlocked = True; st.rerun()
            else: st.error("Wrong password 💔")
        if c2.button("Cancel", key="cancel_pwd", use_container_width=True):
            st.session_state.edit = st.session_state.del_mode = False; st.rerun()
        st.stop()

    if not _readonly and st.session_state.del_mode:
        st.markdown(f'<div class="danger-box"><p class="danger-title">🗑️ Delete “{m["title"]}” forever?</p>'
                    '<p class="danger-text">This cannot be undone — the story and all its photos will be gone.</p></div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete it", key="confirm_del", use_container_width=True, type="primary"):
            delete_moment(active); st.session_state.del_mode = st.session_state.unlocked = False
            st.query_params.clear(); st.rerun()
        if c2.button("No, keep it", key="cancel_del", use_container_width=True):
            st.session_state.del_mode = False; st.rerun()
        st.stop()

    if not _readonly and st.session_state.edit:
        st.markdown('<div class="add-panel"><h2 class="add-title">✏️ Edit this Moment</h2></div>', unsafe_allow_html=True)
        existing = imgs_of(m)
        try: dd = datetime.strptime(m["date"], "%d %b %Y").date()
        except Exception: dd = datetime.now().date()
        ei = EMOJIS.index(m["emoji"]) if m["emoji"] in EMOJIS else 0
        if existing:
            st.markdown("**Current photos** — untick any you want to remove.")
            cols = st.columns(min(len(existing), 4))
            for i, path in enumerate(existing):
                if path: cols[i % len(cols)].image(path, use_container_width=True)
        with st.form(f"edit_{active}"):
            c1, c2 = st.columns([2, 1])
            t = c1.text_input("Title", value=m["title"])
            e = c2.selectbox("Emoji", EMOJIS, index=ei)
            dv = st.date_input("Date", value=dd)
            ab = st.text_area("Our Story", value=m["about"], height=180)
            keep = st.multiselect("Keep which existing photos?", list(range(len(existing))),
                                  list(range(len(existing))), format_func=lambda i: f"Photo {i+1}") if existing else []
            nf = st.file_uploader("Add new photos (auto-compressed)", accept_multiple_files=True, type=["png","jpg","jpeg","webp","gif"])
            cs, cc = st.columns(2)
            if cs.form_submit_button("Save changes 💾", use_container_width=True):
                if not t.strip(): st.warning("Title is required.")
                else:
                    update_moment(active, t, dv.strftime("%d %b %Y"), e, ab, [existing[i] for i in keep], nf or [])
                    st.success("Updated 💖"); st.session_state.edit = st.session_state.unlocked = False; st.rerun()
            if cc.form_submit_button("Cancel", use_container_width=True):
                st.session_state.edit = st.session_state.unlocked = False; st.rerun()
        st.stop()

    tint = AMBIENT.get(m["emoji"], AMBIENT["💖"])
    imgs = [p for p in imgs_of(m) if p]
    if len(imgs) == 1: gal = f'<div class="gallery"><img class="single" src="{imgs[0]}" loading="lazy"/></div>'
    elif len(imgs) > 1: gal = '<div class="gallery">' + "".join(f'<img src="{p}" loading="lazy"/>' for p in imgs) + '</div>'
    else: gal = '<div class="no-photo"><span class="no-photo-emoji">📷</span><div class="no-photo-text">No photos for this moment yet.</div></div>'
    story = m["about"] or '<span class="detail-empty-story">No story written yet.</span>'
    st.markdown(f"""<div class="detail-wrap">
      <div class="detail-ambient" style="background:radial-gradient(circle at 30% 20%, {tint[0]} 0%, transparent 60%),radial-gradient(circle at 70% 80%, {tint[1]} 0%, transparent 60%)"></div>
      <div class="detail-hero"><span class="detail-emoji">{m['emoji']}</span>
        <div class="detail-title">{m['title']}</div><span class="detail-date">{m['date']}</span></div>
      {gal}
      <div class="detail-about"><span class="detail-label">Our Story</span>{story}</div></div>""", unsafe_allow_html=True)

    if prev_slug or next_slug:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        cp, cm, cn = st.columns([2, 1, 2])
        with cp:
            if prev_slug and st.button("← Previous moment", key="prev_bot", use_container_width=True):
                st.query_params["m"] = prev_slug; st.rerun()
        with cm:
            if st.button("⌂ Home", key="home_bot", use_container_width=True):
                st.query_params.clear(); st.rerun()
        with cn:
            if next_slug and st.button("Next moment →", key="next_bot", use_container_width=True):
                st.query_params["m"] = next_slug; st.rerun()

# ═══ 3) TIMELINE ═══════════════════════════════════════════════════════════
else:
    if not MOMENTS:
        st.markdown("""<div class="empty-state"><span class="empty-emoji">🌱</span>
          <div class="empty-title">Our story is just beginning…</div>
          <div class="empty-text">No moments yet. Click <b>✚ Add Moment</b> in the top-right corner to write the very first page of our diary.</div>
          <div class="empty-hint">✚ Add Moment</div></div>""", unsafe_allow_html=True)
    else:
        with st.form("search_form", clear_on_submit=False):
            sc1, sc2 = st.columns([5, 1])
            with sc1:
                q = st.text_input("Search", value=_search, placeholder="🔍  Search titles and stories…",
                                  label_visibility="collapsed", key="search_input")
            with sc2: submitted = st.form_submit_button("Go", use_container_width=True)
            if submitted:
                if q.strip(): st.query_params["q"] = q.strip()
                else: st.query_params.pop("q", None)
                st.rerun()

        if _search:
            sl = _search.lower()
            filtered = {k: v for k, v in MOMENTS.items()
                        if sl in (v.get("title") or "").lower() or sl in (v.get("about") or "").lower()}
            st.markdown(f'<div class="search-hint">Showing <b>{len(filtered)}</b> of {len(MOMENTS)} for “{_search}” &nbsp;·&nbsp; <a href="?" style="color:#c2185b;text-decoration:underline">clear</a></div>', unsafe_allow_html=True)
        else: filtered = MOMENTS

        if not filtered:
            st.markdown('<div class="empty-state"><span class="empty-emoji">🔍</span><div class="empty-title">No moments match</div><div class="empty-text">Try another word, or clear the search.</div></div>', unsafe_allow_html=True)
        else:
            items = "".join(
                f'<div class="tl-item {"left" if i%2==0 else "right"}" id="mm-{i}" style="--d:{i*.12:.2f}s">'
                f'<div class="tl-heart"><svg viewBox="0 0 32 32"><defs>'
                f'<radialGradient id="hg{i}" cx="35%" cy="30%" r="75%">'
                f'<stop offset="0%" stop-color="#ffd0e0"/><stop offset="55%" stop-color="#c2185b"/>'
                f'<stop offset="100%" stop-color="#6b0f2e"/></radialGradient></defs>'
                f'<path d="{HEART}" fill="url(#hg{i})" stroke="#fff" stroke-width="2.5"/></svg></div>'
                f'<a class="tl-card" href="?m={k}"><div class="tl-content">'
                f'<span class="tl-emoji">{norm(m)["emoji"]}</span>'
                f'<div class="tl-title">{norm(m)["title"]}</div>'
                f'<div class="tl-date">{norm(m)["date"]}</div></div>'
                f'<span class="tl-hover-text">Visit The Moment</span></a></div>'
                for i, (k, m) in enumerate(filtered.items()))
            st.markdown(f'<div class="timeline">{items}</div>', unsafe_allow_html=True)

            if not _search:
                dots = "".join(f'<a href="?m={k}" title="{norm(m)["title"][:30]}"></a>' for k, m in filtered.items())
                st.markdown(f'<div class="mini-map">{dots}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="ending-card"><span class="ending-heart">❤️</span>'
            '<div class="ending-title">And the story continues…</div>'
            '<div class="ending-text">Every day with you becomes another page. '
            'These are just the ones we\'ve written so far — there are so many more chapters still waiting for us.</div>'
            '<div class="ending-dots">• • •</div></div>', unsafe_allow_html=True)

        reasons_html = "".join(
            f'<div class="reason-card"><span class="rnum">Reason {i+1}</span>{r}</div>'
            for i, r in enumerate(REASONS))
        st.markdown(
            f'<div class="reasons-wrap">'
            f'<h2 class="reasons-head">Reasons Why I Love You</h2>'
            f'<div class="reasons-track" id="reasonsTrack">{reasons_html}</div>'
            f'<div class="reasons-nav">'
            f'<button type="button" class="reasons-btn" id="reasonsPrev">←</button>'
            f'<span class="reasons-count">✦</span>'
            f'<button type="button" class="reasons-btn" id="reasonsNext">→</button>'
            f'</div></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="love-note"><div class="love-note-line"></div>'
        '<div class="love-note-text">I Love You Avni!!</div>'
        '<div class="love-note-sub">— forever &amp; always —</div>'
        '<div class="love-note-line"></div></div>', unsafe_allow_html=True)
