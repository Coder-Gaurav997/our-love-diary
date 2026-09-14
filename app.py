"""🌿 Avrav Love Diary — Supabase edition (max contrast, no wash)."""
import pathlib, random, uuid
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

st.set_page_config(page_title="Our Love Diary", page_icon="❤️", layout="centered")

try:
    SB_URL = st.secrets["SUPABASE_URL"]
    SB_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    st.error("🔑 Supabase credentials missing.")
    st.stop()

BUCKET, TABLE = "moments-images", "moments"

@st.cache_resource
def _sb() -> Client:
    return create_client(SB_URL, SB_KEY)

supabase = _sb()

START, PWD = "2026-05-01", "gaurav&avni"
EMOJIS = ["💖","💌","🌙","☕","💗","✈️","💍","🌸","🎂","🎄","🌊","⭐","🎁","✨"]
DEFAULTS = {"title": "Untitled Moment", "date": "—", "emoji": "💖", "about": "", "images": []}

for k in ("show_add", "unlocked", "edit", "del_mode"):
    st.session_state.setdefault(k, False)

# ═══════════════════════════════════════════════════════════════════════════
#  DATA LAYER
# ═══════════════════════════════════════════════════════════════════════════
def _load() -> dict:
    try:
        rows = (supabase.table(TABLE)
                .select("slug,title,date,emoji,about,images,created_at")
                .order("created_at").execute().data) or []
    except Exception as e:
        st.error(f"Could not load moments — {e}")
        return {}
    out = {}
    for r in rows:
        slug = r.get("slug") or str(r.get("id"))
        out[slug] = {
            "title":  r.get("title")  or "Untitled Moment",
            "date":   r.get("date")   or "—",
            "emoji":  r.get("emoji")  or "💖",
            "about":  r.get("about")  or "",
            "images": r.get("images") or [],
        }
    return out

def _key_for(title, existing):
    base = "".join(c if c.isalnum() else "_" for c in title.lower())[:40] or "moment"
    key, i = base, 1
    while key in existing:
        key, i = f"{base}_{i}", i + 1
    return key

def _upload(f):
    ext = (pathlib.Path(f.name).suffix.lower() or ".jpg")[:8]
    name = f"{uuid.uuid4().hex}{ext}"
    try:
        supabase.storage.from_(BUCKET).upload(
            path=name, file=bytes(f.getbuffer()),
            file_options={"content-type": f.type or "image/jpeg", "upsert": "true"})
        return supabase.storage.from_(BUCKET).get_public_url(name)
    except Exception as e:
        st.error(f"Upload failed — {e}"); return ""

def _rm(url):
    if not url or not url.startswith("http"): return
    try:
        name = url.split(f"/{BUCKET}/")[-1].split("?")[0]
        supabase.storage.from_(BUCKET).remove([name])
    except Exception: pass

def add_moment(title, date, emoji, about, files):
    existing = _load(); slug = _key_for(title, existing)
    paths = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).insert({
            "slug": slug, "title": title.strip(), "date": date.strip(),
            "emoji": emoji, "about": about.strip(), "images": paths}).execute()
    except Exception as e:
        st.error(f"Could not save — {e}")

def update_moment(slug, title, date, emoji, about, keep, files):
    for old in (MOMENTS.get(slug, {}).get("images") or []):
        if old not in keep: _rm(old)
    new = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).update({
            "title": title.strip(), "date": date.strip(), "emoji": emoji,
            "about": about.strip(), "images": list(keep) + new}).eq("slug", slug).execute()
    except Exception as e:
        st.error(f"Could not update — {e}")

def delete_moment(slug):
    for img in (MOMENTS.get(slug, {}).get("images") or []): _rm(img)
    try:
        supabase.table(TABLE).delete().eq("slug", slug).execute()
    except Exception as e:
        st.error(f"Could not delete — {e}")

MOMENTS = _load()

def norm(m):
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (m or {}).items() if v is not None})
    if not isinstance(out.get("images"), list):
        out["images"] = [out["images"]] if out.get("images") else []
    out["title"] = (out.get("title") or "Untitled Moment").strip()
    out["date"]  = (out.get("date")  or "—").strip()
    out["emoji"] = (out.get("emoji") or "💖").strip()
    out["about"] = (out.get("about") or "").strip()
    return out

def img_src(path): return path or ""
def imgs_of(m): return [p for p in norm(m)["images"] if p]

# ═══════════════════════════════════════════════════════════════════════════
#  PARTICLES — only bokeh + bubbles + leaves + dots (no aurora, no cursor glow)
# ═══════════════════════════════════════════════════════════════════════════
rng = random.Random(42)
def _p(cls, n):
    return "".join(
        f'<span class="{cls}" style="left:{rng.uniform(0,100):.1f}%;'
        + (f'top:{rng.uniform(0,100):.1f}%;' if cls == "dot" else '')
        + f'--d:{rng.uniform(0,14):.1f}s;--t:{rng.uniform(8,15):.1f}s;'
        f'--s:{rng.uniform(2 if cls == "dot" else 9, 5 if cls == "dot" else 28):.1f}px;'
        f'--x:{rng.uniform(-90,90):.0f}px"></span>' for _ in range(n))

def _bokeh(n=4):
    return "".join(
        f'<span class="bokeh" style="left:{rng.uniform(0,100):.1f}%;'
        f'top:{rng.uniform(0,100):.1f}%;--bs:{rng.uniform(28,60):.0f}px;'
        f'--bd:{rng.uniform(0,8):.1f}s;--bt:{rng.uniform(6,11):.1f}s"></span>'
        for _ in range(n))

PARTICLES = (
    '<div class="living-bg" id="living-bg">'
    f'{_bokeh(4)}'
    f'{_p("bubble",8)}{_p("leaf",6)}{_p("dot",14)}'
    '</div>'
)

# ═══════════════════════════════════════════════════════════════════════════
#  CSS — MAX CONTRAST (solid cards, no washes)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&family=Cormorant+Garamond:ital,wght@1,800&family=Lora:ital,wght@1,700&family=Inter:wght@500;600;700;800&family=Dancing+Script:wght@700&display=swap');

  header[data-testid="stHeader"],[data-testid="manage-app-button"],
  #MainMenu,footer,.stDeployButton{display:none !important;visibility:hidden !important}

  :root{color-scheme:light only}
  /* Deep rich gradient */
  .stApp{background:linear-gradient(110deg,#a33f6e 0%,#2d6ea3 100%);background-attachment:fixed}
  .block-container{padding-top:2rem;max-width:1080px;position:relative;z-index:3}

  /* ═══ BACKGROUND (only soft particles, no color washes) ═════════ */
  .living-bg{position:fixed;inset:0;overflow:hidden;pointer-events:none;
    z-index:1;transform:translateZ(0)}

  .bokeh{position:absolute;width:var(--bs);height:var(--bs);border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,.75) 0%,rgba(255,210,230,.3) 35%,transparent 70%);
    opacity:0;pointer-events:none;transform:translateZ(0);
    animation:bokehFloat var(--bt) ease-in-out var(--bd) infinite alternate}
  @keyframes bokehFloat{
    0%{opacity:.25;transform:translate3d(0,0,0) scale(1)}
    100%{opacity:.55;transform:translate3d(15px,-25px,0) scale(1.2)}}

  .bubble{position:absolute;bottom:-50px;width:var(--s);height:var(--s);border-radius:50%;
    background:radial-gradient(circle at 30% 28%,rgba(255,255,255,.95) 0%,rgba(255,255,255,.35) 28%,rgba(180,220,255,.20) 55%,rgba(255,255,255,.05) 100%);
    border:1px solid rgba(255,255,255,.55);
    box-shadow:inset -2px -3px 6px rgba(255,255,255,.55),inset 2px 2px 4px rgba(120,180,240,.35),0 0 10px rgba(255,255,255,.45);
    animation:rise var(--t) linear var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes rise{
    0%{transform:translate3d(0,0,0) scale(.5);opacity:0}10%{opacity:.95}
    50%{transform:translate3d(calc(var(--x)*.6),-50vh,0) scale(1);opacity:.85}90%{opacity:.55}
    100%{transform:translate3d(var(--x),-110vh,0) scale(1.15);opacity:0}}
  .leaf{position:absolute;top:-50px;width:var(--s);height:calc(var(--s)*.6);
    background:linear-gradient(135deg,#a4e07a 0%,#4caf50 55%,#2e7d32 100%);border-radius:50% 0 50% 0;
    box-shadow:inset -1px -1px 3px rgba(0,0,0,.20),inset 1px 1px 2px rgba(255,255,255,.35),0 3px 6px rgba(0,0,0,.15);
    animation:fall-leaf var(--t) linear var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes fall-leaf{
    0%{transform:translate3d(0,-10vh,0) rotate(0) rotateY(0);opacity:0}8%{opacity:.9}
    50%{transform:translate3d(calc(var(--x)*.5),50vh,0) rotate(360deg) rotateY(180deg)}90%{opacity:.75}
    100%{transform:translate3d(var(--x),115vh,0) rotate(720deg) rotateY(360deg);opacity:0}}
  .dot{position:absolute;width:var(--s);height:var(--s);border-radius:50%;background:#fff;
    box-shadow:0 0 5px rgba(255,255,255,.95),0 0 12px rgba(255,246,200,.85),0 0 22px rgba(255,240,180,.55);
    animation:twinkle var(--t) ease-in-out var(--d) infinite;opacity:0;transform:translateZ(0)}
  @keyframes twinkle{0%,100%{opacity:0;transform:scale(.4)}50%{opacity:1;transform:scale(1.35)}}

  @keyframes fadeInDown{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:none}}
  @keyframes fadeInUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}

  /* ═══ TITLE — pure black with heavy white outline ═══════════════ */
  h1.love-title{
    font-family:'Great Vibes',cursive !important;text-align:center;font-size:5.5rem;
    font-weight:600;color:#000000;margin:0;
    -webkit-text-stroke:5px #ffffff;paint-order:stroke fill;
    text-shadow:
      0 2px 0 #ffffff,
      0 5px 20px rgba(0,0,0,.85),
      0 0 28px rgba(255,255,255,1),
      0 0 50px rgba(255,255,255,.8);
    animation:fadeInDown 1s cubic-bezier(.2,.8,.2,1) both}

  /* ═══ SUBHEADING — solid white, pure black text ═════════════════ */
  p.love-sub{
    font-family:'Cormorant Garamond',serif !important;
    font-weight:800;font-style:italic;text-align:center;
    font-size:1.2rem;letter-spacing:.35em;text-transform:uppercase;color:#000000;
    margin:.9rem auto 0 auto;display:inline-block;padding:.55rem 1.6rem;
    border:3px solid #000000;border-radius:999px;
    background:#ffffff;
    box-shadow:0 10px 26px rgba(0,0,0,.5);
    animation:fadeInUp .9s .15s cubic-bezier(.2,.8,.2,1) both}

  /* ═══ TIMELINE ══════════════════════════════════════════════════ */
  .timeline{position:relative;max-width:920px;margin:10px auto 30px auto;padding:30px 0;
    contain:layout paint style}
  .timeline::before{content:'';position:absolute;left:50%;top:0;bottom:0;width:5px;
    transform:translateX(-50%);border-radius:4px;
    background:linear-gradient(180deg,transparent 0%,#000000 8%,#c2185b 50%,#000000 92%,transparent 100%)}
  .tl-item{position:relative;width:50%;padding:20px 60px;box-sizing:border-box;
    opacity:0;transform:translateY(28px);
    animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:var(--d)}
  .tl-item.left{left:0;text-align:right}.tl-item.right{left:50%;text-align:left}
  .tl-heart{position:absolute;top:28px;width:36px;height:36px;z-index:3;
    filter:drop-shadow(0 3px 10px rgba(0,0,0,.75));
    animation:beat 2.4s ease-in-out infinite}
  @keyframes beat{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
  .tl-item.left .tl-heart{right:-18px}.tl-item.right .tl-heart{left:-18px}
  .tl-heart svg{width:100%;height:100%}

  /* ═══ TILES — 100% solid white, pure black border ═══════════════ */
  a.tl-card,a.tl-card:visited,a.tl-card:hover,a.tl-card:active{
    text-decoration:none;color:inherit}
  .tl-card{
    display:inline-block;padding:18px 26px;border-radius:18px;
    background:#ffffff;
    border:3px solid #000000;
    box-shadow:0 12px 32px rgba(0,0,0,.5);
    transition:transform .3s cubic-bezier(.2,.8,.2,1),
               box-shadow .3s ease,border-color .3s ease;
    text-align:inherit;position:relative;overflow:hidden;cursor:pointer;
    min-width:240px;min-height:96px;transform-style:preserve-3d}
  .tl-card:hover{
    transform:translateY(-5px) scale(1.03);
    border-color:#7a0a1e;
    box-shadow:0 22px 48px rgba(0,0,0,.65)}
  .tl-content{display:block;transition:opacity .25s ease}
  .tl-card:hover .tl-content{opacity:0}
  .tl-hover-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.6rem;color:#000000;
    opacity:0;transform:scale(.94);
    transition:opacity .25s ease,transform .25s ease;
    pointer-events:none;text-align:center;padding:0 12px}
  .tl-card:hover .tl-hover-text{opacity:1;transform:scale(1)}
  .tl-emoji{display:inline-block;font-size:1.3rem;margin-bottom:4px}
  .tl-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.55rem;
    color:#000000;line-height:1.25;margin:2px 0 8px 0}
  .tl-date{display:inline-block;font-family:'Cormorant Garamond',serif;
    font-style:italic;font-weight:700;font-size:.92rem;letter-spacing:.22em;
    text-transform:uppercase;color:#000000;padding:5px 16px;
    border-radius:999px;background:#ffd0e0;border:2.5px solid #000000}

  /* ═══ ALL CARDS — solid white, black borders ════════════════════ */
  .empty-state,.no-photo,.ending-card,.add-panel,.danger-box,.detail-about{
    background:#ffffff;
    border:3px solid #000000;
    box-shadow:0 16px 40px rgba(0,0,0,.5)}

  .empty-state{max-width:640px;margin:40px auto;padding:50px 40px;border-radius:24px;
    text-align:center;animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) both}
  .empty-emoji{font-size:3rem;display:block;margin-bottom:12px}
  .empty-title{font-family:'Great Vibes',cursive;font-size:2.5rem;color:#000000;margin:0 0 10px 0}
  .empty-text{font-family:'Lora',serif;font-style:italic;font-size:1.08rem;
    color:#000000;line-height:1.7}
  .empty-hint{display:inline-block;margin-top:16px;font-family:'Inter',sans-serif;font-weight:800;
    font-size:.85rem;letter-spacing:.14em;text-transform:uppercase;color:#ffffff;
    padding:10px 22px;border-radius:999px;
    background:linear-gradient(135deg,#000000 0%,#0d3b25 55%,#1c6b3f 100%);
    border:2.5px solid #000000;
    box-shadow:0 8px 20px rgba(0,0,0,.55)}

  .no-photo{max-width:820px;margin:24px auto 22px auto;padding:56px 30px;
    border-radius:20px;text-align:center;border-style:dashed}
  .no-photo-emoji{font-size:3rem;display:block;margin-bottom:10px}
  .no-photo-text{font-family:'Lora',serif;font-style:italic;font-size:1.1rem;color:#000000}

  /* ═══ ENDING CARD ═══════════════════════════════════════════════ */
  .ending-card{max-width:720px;margin:30px auto 20px auto;padding:34px 40px;border-radius:24px;
    text-align:center;position:relative;overflow:hidden;border-style:dashed;
    animation:fadeInUp 1s .6s cubic-bezier(.2,.8,.2,1) both}
  .ending-heart{font-size:2.3rem;display:block;margin-bottom:8px;
    animation:beat 2.4s ease-in-out infinite}
  .ending-title{font-family:'Great Vibes',cursive;font-size:2.8rem;color:#000000;
    margin:4px 0 10px 0}
  .ending-text{font-family:'Lora',serif;font-style:italic;font-weight:500;font-size:1.1rem;
    color:#000000;line-height:1.75}
  .ending-dots{margin-top:16px;letter-spacing:1em;font-size:1.5rem;color:#c2185b;
    animation:fadeInOut 2.6s ease-in-out infinite}
  @keyframes fadeInOut{0%,100%{opacity:.6}50%{opacity:1}}

  /* ═══ LOVE NOTE ═════════════════════════════════════════════════ */
  .love-note{max-width:720px;margin:10px auto 70px auto;padding:30px 20px;text-align:center;
    animation:fadeInUp 1.2s .9s cubic-bezier(.2,.8,.2,1) both}
  .love-note-line{width:170px;height:3px;margin:0 auto;
    background:linear-gradient(90deg,transparent,#000000 40%,#000000 60%,transparent);
    border-radius:2px}
  .love-note-text{font-family:'Dancing Script',cursive;font-weight:700;font-size:4.5rem;color:#c2185b;
    margin:14px 0 8px 0;line-height:1.15;
    text-shadow:
      0 0 16px rgba(255,92,138,.8),
      0 4px 16px rgba(0,0,0,.8),
      0 2px 0 #ffffff;
    -webkit-text-stroke:1.8px #ffffff;paint-order:stroke fill;
    animation:lovePulse 3s ease-in-out infinite}
  @keyframes lovePulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
  .love-note-sub{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:800;
    font-size:1.2rem;letter-spacing:.35em;text-transform:uppercase;color:#000000;margin:0 0 18px 0;
    text-shadow:0 1px 4px rgba(255,255,255,.9)}

  /* ═══ DETAIL PAGE ═══════════════════════════════════════════════ */
  .detail-wrap{max-width:880px;margin:10px auto 40px auto;
    animation:fadeInUp .8s cubic-bezier(.2,.8,.2,1) both}
  .detail-hero{text-align:center;margin:10px 0 18px 0}
  .detail-emoji{font-size:3.5rem;display:block;margin-bottom:6px;
    filter:drop-shadow(0 4px 12px rgba(0,0,0,.7))}
  .detail-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:2.8rem;
    color:#000000;margin:6px 0 12px 0;line-height:1.15;
    text-shadow:0 2px 12px rgba(255,255,255,1), 0 1px 0 #ffffff}
  .detail-date{display:inline-block;font-family:'Cormorant Garamond',serif;
    font-style:italic;font-weight:700;font-size:1rem;letter-spacing:.28em;
    text-transform:uppercase;color:#000000;padding:7px 22px;border-radius:999px;
    background:#ffd0e0;border:2.5px solid #000000;
    box-shadow:0 6px 18px rgba(0,0,0,.4)}

  .gallery{display:grid;gap:14px;margin:24px auto 22px auto;max-width:820px;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
  .gallery img{width:100%;height:220px;object-fit:cover;border-radius:18px;
    border:4px solid #000000;box-shadow:0 14px 32px rgba(0,0,0,.6);
    transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease;cursor:pointer;
    filter:contrast(1.08) saturate(1.08) brightness(1.02)}
  .gallery img:hover{transform:translateY(-6px) scale(1.03);box-shadow:0 22px 48px rgba(0,0,0,.75)}
  .gallery img.single{grid-column:1/-1;height:auto;max-height:520px}

  .detail-about{max-width:820px;margin:0 auto;padding:28px 32px;border-radius:20px;
    font-family:'Lora',serif;font-style:italic;font-weight:500;
    font-size:1.22rem;line-height:1.85;color:#000000;position:relative;overflow:hidden}
  .detail-label{display:block;font-family:'Cormorant Garamond',serif;
    font-style:italic;font-weight:800;font-size:.88rem;letter-spacing:.28em;
    text-transform:uppercase;color:#4a0312;margin-bottom:8px}
  .detail-empty-story{opacity:.7;font-style:italic}

  /* ═══ BUTTONS — very dark green, pure white text ════════════════ */
  .stButton>button{
    background:linear-gradient(135deg,#000000 0%,#0a3320 55%,#155f34 100%);
    border:3px solid #000000;color:#ffffff;
    font-family:'Inter',sans-serif;font-weight:800;letter-spacing:.04em;
    border-radius:999px;white-space:nowrap;
    text-shadow:0 2px 4px rgba(0,0,0,.9), 0 1px 2px rgba(0,0,0,1);
    box-shadow:
      0 12px 28px rgba(0,0,0,.65),
      inset 0 1px 2px rgba(255,255,255,.3);
    transition:transform .25s cubic-bezier(.2,.8,.2,1),
               box-shadow .25s ease,background .25s ease}
  .stButton>button:hover{
    background:linear-gradient(135deg,#052015 0%,#0f4a28 55%,#1c7a44 100%);
    border-color:#000000;
    transform:translateY(-2px) scale(1.03);
    box-shadow:0 18px 38px rgba(0,0,0,.8),
               inset 0 1px 3px rgba(255,255,255,.5)}
  .stButton>button:active{transform:translateY(0) scale(.97)}
  .stButton>button p{color:#ffffff !important;font-weight:800 !important}
  .stButton>button[kind="secondary"]{padding:.45rem 1.15rem;font-size:.9rem}
  .stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#1a0008 0%,#5a0318 45%,#a10a4a 100%);
    border-color:#000000;padding:.45rem 1.15rem;font-size:.9rem}
  .stButton>button[kind="primary"]:hover{
    background:linear-gradient(135deg,#3a020f 0%,#7a0a1e 45%,#c2185b 100%);
    border-color:#000000}

  /* ═══ FORM INPUTS ═══════════════════════════════════════════════ */
  .stTextInput input,.stTextArea textarea,.stDateInput input{
    background:#ffffff !important;color:#000000 !important;
    border-radius:14px !important;border:3px solid #000000 !important;
    font-family:'Lora',serif !important;font-weight:700 !important;font-size:1.05rem !important;
    box-shadow:inset 0 2px 6px rgba(0,0,0,.08) !important;
    transition:all .25s ease !important}
  .stTextInput input:focus,.stTextArea textarea:focus,.stDateInput input:focus{
    border-color:#c2185b !important;
    box-shadow:0 0 0 3px rgba(194,24,91,.4),inset 0 2px 6px rgba(0,0,0,.08) !important}
  .stTextInput input::placeholder,.stTextArea textarea::placeholder{
    color:#4a0312 !important;font-style:italic !important;opacity:.85 !important}
  .stTextInput label,.stTextArea label,.stDateInput label,.stSelectbox label,
  .stFileUploader label,.stMultiSelect label{
    color:#000000 !important;font-family:'Cormorant Garamond',serif !important;
    font-style:italic !important;font-weight:800 !important;
    letter-spacing:.15em !important;font-size:1.15rem !important}
  .stSelectbox div[data-baseweb="select"]>div,
  .stMultiSelect div[data-baseweb="select"]>div{
    background:#ffffff !important;border:3px solid #000000 !important;
    border-radius:14px !important;color:#000000 !important;
    font-family:'Lora',serif !important;font-weight:700 !important}
  .stFileUploader section{background:#ffffff !important;
    border:3px dashed #000000 !important;border-radius:16px !important;
    transition:all .25s ease !important}
  .stFileUploader section:hover{border-color:#c2185b !important}
  section[data-testid="stFileUploadDropzone"]{color:#000000 !important}
  section[data-testid="stFileUploadDropzone"] button{
    background:linear-gradient(135deg,#000000 0%,#0a3320 55%,#155f34 100%) !important;
    color:#ffffff !important;border:2.5px solid #000000 !important;
    border-radius:999px !important;font-family:'Inter',sans-serif !important;
    font-weight:800 !important}

  .add-panel{max-width:720px;margin:10px auto 30px auto;padding:28px 32px;border-radius:22px;
    animation:fadeInUp .7s cubic-bezier(.2,.8,.2,1) both}
  .add-title,.add-panel h2,h2.add-title,
  [data-testid="stMarkdownContainer"] h2.add-title,
  [data-testid="stMarkdownContainer"] .add-panel h2{
    font-family:'Great Vibes',cursive !important;font-size:2.8rem !important;
    font-weight:600 !important;text-align:center !important;margin:0 0 8px 0 !important;
    color:#000000 !important;-webkit-text-fill-color:#000000 !important;
    -webkit-text-stroke:0 !important;opacity:1 !important}

  .danger-box{max-width:720px;margin:16px auto;padding:24px 28px;border-radius:18px;
    text-align:center;border-style:dashed;background:#ffffff;
    animation:fadeInUp .5s ease-out both}
  .danger-title{font-family:'Lora',serif;font-style:italic;font-weight:800;
    font-size:1.45rem;color:#4a0312;margin:0 0 8px 0}
  .danger-text{font-family:'Lora',serif;font-style:italic;color:#000000;font-size:1.02rem}

  @keyframes confettiFloat{
    0%{opacity:1;transform:translate(-50%,-50%) scale(.8)}
    100%{opacity:0;transform:translate(calc(-50% + var(--dx)),calc(-50% + var(--dy))) scale(1.4) rotate(15deg)}}

  @media (max-width:680px){
    .timeline::before{left:22px}
    .tl-item{width:100%;left:0 !important;text-align:left !important;padding:18px 20px 18px 62px}
    .tl-item.left .tl-heart,.tl-item.right .tl-heart{left:5px;right:auto}
    .detail-title{font-size:2.1rem}.detail-about{font-size:1.1rem;padding:22px 24px}
    .tl-hover-text{font-size:1.35rem}.gallery{grid-template-columns:1fr}
    h1.love-title{font-size:3.6rem;-webkit-text-stroke:4px #fff}
    .love-note-text{font-size:3rem}.love-note-sub{font-size:1rem;letter-spacing:.25em}
    .add-title,[data-testid="stMarkdownContainer"] h2.add-title{font-size:2.2rem !important}}

  @media (prefers-reduced-motion: reduce){
    .bokeh,.bubble,.leaf,.dot,.tl-heart,.ending-heart,.ending-dots,.love-note-text{animation:none !important}}
</style>
""", unsafe_allow_html=True)

st.markdown(PARTICLES, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
#  JS — no cursor glow, no aurora
# ═══════════════════════════════════════════════════════════════════════════
components.html("""<script>
(function(){
  const p = window.parent.document;
  const bg = p.getElementById('living-bg');
  if (bg) {
    let r = false;
    p.addEventListener('scroll', () => {
      if (r) return; r = true;
      requestAnimationFrame(() => {
        const y = p.documentElement.scrollTop || p.body.scrollTop || 0;
        bg.style.transform = 'translate3d(0,' + (y * 0.3) + 'px,0)';
        r = false;
      });
    }, { passive: true });
  }
  if (!matchMedia('(hover: none)').matches) {
    let card = null, rect = null, mx = 0, my = 0, busy = false;
    p.addEventListener('mouseover', e => {
      const c = e.target.closest && e.target.closest('.tl-card');
      if (c && c !== card) { card = c; rect = c.getBoundingClientRect(); }
    }, { passive: true });
    p.addEventListener('mouseout', e => {
      const c = e.target.closest && e.target.closest('.tl-card');
      if (c && c === card) { c.style.transform = ''; card = null; rect = null; }
    }, { passive: true });
    p.addEventListener('mousemove', e => {
      if (!card) return;
      mx = e.clientX; my = e.clientY;
      if (busy) return; busy = true;
      requestAnimationFrame(() => {
        busy = false;
        if (!card || !rect) return;
        const x = (mx - rect.left) / rect.width - 0.5;
        const y = (my - rect.top) / rect.height - 0.5;
        card.style.transform =
          'perspective(700px) rotateY(' + (x * 6) + 'deg) rotateX(' + (-y * 6) +
          'deg) translateY(-5px) scale(1.02)';
      });
    }, { passive: true });
  }
  let lastBurst = 0;
  p.addEventListener('click', e => {
    const t = e.target;
    if (t.closest('button,input,textarea,select,[data-testid="stFileUploaderDropzone"]')) return;
    const now = Date.now();
    if (now - lastBurst < 150) return;
    lastBurst = now;
    const glyphs = ['❤️','💖','💕','💗','💘','🌸'];
    for (let i = 0; i < 3; i++) {
      const h = p.createElement('span');
      h.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
      h.style.cssText =
        'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;' +
        'font-size:' + (14 + Math.random() * 10) + 'px;pointer-events:none;z-index:99999;' +
        'animation:confettiFloat ' + (0.9 + Math.random() * 0.6) + 's ease-out forwards;' +
        'transform:translate(-50%,-50%);will-change:transform,opacity;';
      h.style.setProperty('--dx', (Math.random() - 0.5) * 180 + 'px');
      h.style.setProperty('--dy', -(60 + Math.random() * 100) + 'px');
      p.body.appendChild(h);
      setTimeout(() => h.remove(), 1600);
    }
  }, { passive: true });
  window.parent.postMessage({ isStreamlitMessage: true,
    type: 'streamlit:setFrameHeight', height: 0 }, '*');
})();
</script>""", height=0)

# ── Top bar ──────────────────────────────────────────────────────────────
_, cb = st.columns([8, 2])
with cb:
    if st.button("✚ Add Moment", key="add_btn", use_container_width=True):
        st.session_state.show_add = True
        st.session_state.edit = st.session_state.del_mode = False
        st.query_params.clear(); st.rerun()

# ── Header ───────────────────────────────────────────────────────────────
st.markdown('<h1 class="love-title">Our Love Diary</h1>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center"><p class="love-sub">A Little Garden Of Our Favourite Moments!!</p></div>', unsafe_allow_html=True)

components.html(f"""<style>
  body{{margin:0;background:transparent}}
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&display=swap');
  .counter-wrap{{display:flex;justify-content:center;padding:20px 0 6px 0;
    animation:fadeInUp 1s .3s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes fadeInUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:none}}}}
  .days-counter{{display:inline-flex;align-items:center;gap:14px;padding:15px 30px;border-radius:999px;
    background:#ffffff;border:3px solid #000000;
    box-shadow:0 14px 36px rgba(0,0,0,.5);
    font-family:'Inter',sans-serif;color:#000000}}
  .counter-label{{font-weight:800;font-size:.88rem;letter-spacing:.22em;
    text-transform:uppercase;color:#000000}}
  .counter-sep{{width:2px;height:30px;
    background:linear-gradient(180deg,transparent,#000000,transparent);opacity:.85}}
  .counter-unit{{display:inline-flex;align-items:baseline;gap:5px}}
  .counter-unit b{{font-size:1.6rem;font-weight:800;color:#000000;line-height:1;
    font-variant-numeric:tabular-nums;min-width:2.6ch;text-align:right}}
  .counter-unit span{{font-size:.78rem;font-weight:800;letter-spacing:.14em;
    text-transform:uppercase;color:#000000}}
  @media(max-width:680px){{.days-counter{{gap:10px;padding:12px 18px}}
    .counter-unit b{{font-size:1.2rem}}.counter-unit span{{font-size:.7rem}}
    .counter-label{{font-size:.75rem}}}}
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

st.markdown('<hr style="border:none;height:3px;width:90%;margin:1rem auto;background:linear-gradient(90deg,transparent,#000000 15%,#000000 85%,transparent);border-radius:2px">', unsafe_allow_html=True)

# ── Routing ──────────────────────────────────────────────────────────────
active = st.query_params.get("m")
HEART = ('M16 28 C4 18 2 12 2 8 C2 4 5 1 9 1 C12 1 15 3 16 6 C17 3 20 1 23 1 '
         'C27 1 30 4 30 8 C30 12 28 18 16 28 Z')

# ═══ 1) ADD MOMENT ═══════════════════════════════════════════════════════
if st.session_state.show_add:
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
            files = st.file_uploader("Photos (optional)", accept_multiple_files=True,
                                     type=["png","jpg","jpeg","webp","gif"])
            if st.form_submit_button("Save Moment 💾"):
                if not title.strip(): st.warning("Please enter a title.")
                else:
                    add_moment(title, dv.strftime("%d %b %Y"), emoji, about, files or [])
                    st.success(f"Saved “{title}” 💖")
                    st.session_state.show_add = st.session_state.unlocked = False; st.rerun()

# ═══ 2) DETAIL PAGE ══════════════════════════════════════════════════════
elif active and active in MOMENTS:
    m = norm(MOMENTS[active])
    cb_, _, ce, cd = st.columns([3, 4, 1.2, 1.2])
    if cb_.button("← Back to timeline", key="back_d"):
        st.query_params.clear()
        st.session_state.edit = st.session_state.del_mode = False; st.rerun()
    if ce.button("✏️ Edit", key="edit_b", use_container_width=True):
        st.session_state.edit = True; st.session_state.del_mode = False
        st.session_state.unlocked = False; st.rerun()
    if cd.button("🗑️ Delete", key="del_b", use_container_width=True, type="primary"):
        st.session_state.del_mode = True; st.session_state.edit = False
        st.session_state.unlocked = False; st.rerun()

    if (st.session_state.edit or st.session_state.del_mode) and not st.session_state.unlocked:
        st.markdown('<div class="add-panel"><h2 class="add-title">🔒 Unlock to continue</h2></div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", key="pwd_ed")
        c1, c2 = st.columns(2)
        if c1.button("Unlock ✨", key="unlock_ed", use_container_width=True):
            if pwd == PWD: st.session_state.unlocked = True; st.rerun()
            else: st.error("Wrong password 💔")
        if c2.button("Cancel", key="cancel_pwd", use_container_width=True):
            st.session_state.edit = st.session_state.del_mode = False; st.rerun()
        st.stop()

    if st.session_state.del_mode:
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

    if st.session_state.edit:
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
                                  list(range(len(existing))),
                                  format_func=lambda i: f"Photo {i+1}") if existing else []
            nf = st.file_uploader("Add new photos (optional)", accept_multiple_files=True,
                                  type=["png","jpg","jpeg","webp","gif"])
            cs, cc = st.columns(2)
            if cs.form_submit_button("Save changes 💾", use_container_width=True):
                if not t.strip(): st.warning("Title is required.")
                else:
                    update_moment(active, t, dv.strftime("%d %b %Y"), e, ab,
                                  [existing[i] for i in keep], nf or [])
                    st.success("Updated 💖"); st.session_state.edit = st.session_state.unlocked = False; st.rerun()
            if cc.form_submit_button("Cancel", use_container_width=True):
                st.session_state.edit = st.session_state.unlocked = False; st.rerun()
        st.stop()

    imgs = [p for p in imgs_of(m) if p]
    if len(imgs) == 1:
        gal = f'<div class="gallery"><img class="single" src="{imgs[0]}"/></div>'
    elif len(imgs) > 1:
        gal = '<div class="gallery">' + "".join(f'<img src="{p}"/>' for p in imgs) + '</div>'
    else:
        gal = ('<div class="no-photo"><span class="no-photo-emoji">📷</span>'
               '<div class="no-photo-text">No photos for this moment yet.</div></div>')

    story = m["about"] or '<span class="detail-empty-story">No story written yet.</span>'

    st.markdown(f"""<div class="detail-wrap">
      <div class="detail-hero"><span class="detail-emoji">{m['emoji']}</span>
        <div class="detail-title">{m['title']}</div>
        <span class="detail-date">{m['date']}</span></div>
      {gal}
      <div class="detail-about"><span class="detail-label">Our Story</span>{story}</div>
    </div>""", unsafe_allow_html=True)

# ═══ 3) TIMELINE ═════════════════════════════════════════════════════════
else:
    if not MOMENTS:
        st.markdown("""<div class="empty-state">
          <span class="empty-emoji">🌱</span>
          <div class="empty-title">Our story is just beginning…</div>
          <div class="empty-text">No moments yet. Click <b>✚ Add Moment</b> in the top-right corner
            to write the very first page of our diary.</div>
          <div class="empty-hint">✚ Add Moment</div></div>""", unsafe_allow_html=True)
    else:
        items = "".join(
            f'<div class="tl-item {"left" if i%2==0 else "right"}" style="--d:{i*.12:.2f}s">'
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
            for i, (k, m) in enumerate(MOMENTS.items()))
        st.markdown(f'<div class="timeline">{items}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="ending-card">'
        '<span class="ending-heart">❤️</span>'
        '<div class="ending-title">And the story continues…</div>'
        '<div class="ending-text">Every day with you becomes another page. '
        'These are just the ones we\'ve written so far — there are so many more chapters '
        'still waiting for us.</div>'
        '<div class="ending-dots">• • •</div>'
        '</div>'
        '<div class="love-note">'
        '<div class="love-note-line"></div>'
        '<div class="love-note-text">I Love You Avni!!</div>'
        '<div class="love-note-sub">— forever &amp; always —</div>'
        '<div class="love-note-line"></div>'
        '</div>',
        unsafe_allow_html=True,
    )
