"""🌿 Avrav Love Diary — Supabase edition (DB + Storage, no local files)."""
import pathlib, random, uuid
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

st.set_page_config(page_title="Our Love Diary", page_icon="❤️", layout="centered")

# ═══════════════════════════════════════════════════════════════════════════
#  SUPABASE CONNECTION
# ═══════════════════════════════════════════════════════════════════════════
try:
    SB_URL = st.secrets["SUPABASE_URL"]
    SB_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    st.error("🔑 Supabase credentials missing. Add `SUPABASE_URL` and "
             "`SUPABASE_SERVICE_KEY` to `.streamlit/secrets.toml` (local) "
             "or Streamlit Cloud → Settings → Secrets.")
    st.stop()

BUCKET, TABLE = "moments-images", "moments"

@st.cache_resource
def _sb() -> Client:
    return create_client(SB_URL, SB_KEY)

supabase = _sb()

# ═══════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
START, PWD = "2026-05-01", "gaurav&avni"
EMOJIS = ["💖","💌","🌙","☕","💗","✈️","💍","🌸","🎂","🎄","🌊","⭐","🎁","✨"]
DEFAULTS = {"title": "Untitled Moment", "date": "—", "emoji": "💖",
            "about": "", "images": []}

for k in ("show_add", "unlocked", "edit", "del_mode"):
    st.session_state.setdefault(k, False)

# ═══════════════════════════════════════════════════════════════════════════
#  DATA LAYER — all Supabase
# ═══════════════════════════════════════════════════════════════════════════
def _load() -> dict:
    """Fetch all moments → {slug: {...}}. Never raises."""
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

def _key_for(title: str, existing: dict) -> str:
    base = "".join(c if c.isalnum() else "_" for c in title.lower())[:40] or "moment"
    key, i = base, 1
    while key in existing:
        key, i = f"{base}_{i}", i + 1
    return key

def _upload(f) -> str:
    """Upload a Streamlit UploadedFile to Supabase Storage, return public URL."""
    ext = (pathlib.Path(f.name).suffix.lower() or ".jpg")[:8]
    name = f"{uuid.uuid4().hex}{ext}"
    try:
        supabase.storage.from_(BUCKET).upload(
            path=name,
            file=bytes(f.getbuffer()),
            file_options={
                "content-type": f.type or "image/jpeg",
                "upsert": "true",
            },
        )
        return supabase.storage.from_(BUCKET).get_public_url(name)
    except Exception as e:
        st.error(f"Upload failed — {e}")
        return ""

def _rm(url: str) -> None:
    """Delete a file from Supabase Storage given its public URL."""
    if not url or not url.startswith("http"):
        return
    try:
        # URL format: https://xxx.supabase.co/storage/v1/object/public/BUCKET/filename
        name = url.split(f"/{BUCKET}/")[-1].split("?")[0]
        supabase.storage.from_(BUCKET).remove([name])
    except Exception:
        pass

def add_moment(title, date, emoji, about, files):
    existing = _load()
    slug = _key_for(title, existing)
    paths = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).insert({
            "slug": slug,
            "title": title.strip(),
            "date": date.strip(),
            "emoji": emoji,
            "about": about.strip(),
            "images": paths,
        }).execute()
    except Exception as e:
        st.error(f"Could not save — {e}")

def update_moment(slug, title, date, emoji, about, keep, files):
    for old in (MOMENTS.get(slug, {}).get("images") or []):
        if old not in keep:
            _rm(old)
    new = [p for p in (_upload(f) for f in files) if p]
    try:
        supabase.table(TABLE).update({
            "title": title.strip(),
            "date": date.strip(),
            "emoji": emoji,
            "about": about.strip(),
            "images": list(keep) + new,
        }).eq("slug", slug).execute()
    except Exception as e:
        st.error(f"Could not update — {e}")

def delete_moment(slug):
    for img in (MOMENTS.get(slug, {}).get("images") or []):
        _rm(img)
    try:
        supabase.table(TABLE).delete().eq("slug", slug).execute()
    except Exception as e:
        st.error(f"Could not delete — {e}")

# ── Load once per rerun ──────────────────────────────────────────────────
MOMENTS = _load()

# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def norm(m: dict) -> dict:
    """Fill missing fields so downstream code never crashes."""
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (m or {}).items() if v is not None})
    if not isinstance(out.get("images"), list):
        out["images"] = [out["images"]] if out.get("images") else []
    out["title"] = (out.get("title") or "Untitled Moment").strip()
    out["date"]  = (out.get("date")  or "—").strip()
    out["emoji"] = (out.get("emoji") or "💖").strip()
    out["about"] = (out.get("about") or "").strip()
    return out

def img_src(path: str) -> str:
    """Images are already full URLs in Supabase — just pass through."""
    return path or ""

def imgs_of(m: dict) -> list:
    return [p for p in norm(m)["images"] if p]

# ═══════════════════════════════════════════════════════════════════════════
#  PARTICLES + AURORA + BOKEH
# ═══════════════════════════════════════════════════════════════════════════
rng = random.Random(42)
def _p(cls, n):
    return "".join(
        f'<span class="{cls}" style="left:{rng.uniform(0,100):.1f}%;'
        + (f'top:{rng.uniform(0,100):.1f}%;' if cls == "dot" else '')
        + f'--d:{rng.uniform(0,14):.1f}s;--t:{rng.uniform(8,15):.1f}s;'
        f'--s:{rng.uniform(2 if cls == "dot" else 9, 5 if cls == "dot" else 28):.1f}px;'
        f'--x:{rng.uniform(-90,90):.0f}px"></span>' for _ in range(n))

def _bokeh(n=10):
    return "".join(
        f'<span class="bokeh" style="left:{rng.uniform(0,100):.1f}%;'
        f'top:{rng.uniform(0,100):.1f}%;--bs:{rng.uniform(28,70):.0f}px;'
        f'--bd:{rng.uniform(0,8):.1f}s;--bt:{rng.uniform(6,11):.1f}s"></span>'
        for _ in range(n))

PARTICLES = (
    '<div class="living-bg" id="living-bg">'
    '<div class="aurora a1"></div>'
    '<div class="aurora a2"></div>'
    '<div class="aurora a3"></div>'
    f'{_bokeh(10)}'
    f'{_p("bubble",20)}{_p("leaf",16)}{_p("dot",45)}'
    '</div>'
    '<div class="cursor-glow" id="cursor-glow"></div>'
)

# ═══════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&family=Cormorant+Garamond:ital,wght@1,800&family=Lora:ital,wght@1,700&family=Inter:wght@500;600;700&family=Dancing+Script:wght@700&display=swap');
  /* Hide the top header bar (Share, Star, Edit, GitHub, ⋮ menu) */
  header[data-testid="stHeader"] {
      display: none !important;
      visibility: hidden !important;
  }

  /* Hide the bottom-right "Manage app" button */
  [data-testid="manage-app-button"] {
      display: none !important;
      visibility: hidden !important;
  }

  /* Hide the hamburger menu (⋮) */
  #MainMenu {
      display: none !important;
      visibility: hidden !important;
  }

  /* Hide the "Made with Streamlit" footer */
  footer {
      display: none !important;
      visibility: hidden !important;
  }

  /* Hide the Deploy button if it appears */
  .stDeployButton {
      display: none !important;
  }
  :root{color-scheme:light only}
  .stApp{background:linear-gradient(110deg,#F28BA8 0%,#76B7E5 100%);background-attachment:fixed}
  .block-container{padding-top:2rem;max-width:1080px;position:relative;z-index:2}
  header[data-testid="stHeader"]{background:transparent}footer{visibility:hidden}
  .living-bg{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:1;transition:transform .15s linear}
    /* ═══ AURORA WAVES ═══ */
  .aurora{position:absolute;width:70vmax;height:70vmax;border-radius:50%;
    filter:blur(85px);opacity:.55;will-change:transform;pointer-events:none}
  .aurora.a1{top:-30%;left:-20%;
    background:radial-gradient(circle,rgba(255,140,190,.75),transparent 65%);
    animation:auroraFloat 28s ease-in-out infinite}
  .aurora.a2{top:10%;right:-30%;
    background:radial-gradient(circle,rgba(140,170,255,.7),transparent 65%);
    animation:auroraFloat 34s ease-in-out -8s infinite}
  .aurora.a3{bottom:-30%;left:20%;
    background:radial-gradient(circle,rgba(170,230,255,.65),transparent 65%);
    animation:auroraFloat 30s ease-in-out -16s infinite}
  @keyframes auroraFloat{
    0%,100%{transform:translate(0,0) scale(1)}
    33%{transform:translate(8%,6%) scale(1.12)}
    66%{transform:translate(-7%,-5%) scale(.95)}}

  /* ═══ BOKEH LIGHT SPOTS ═══ */
  .bokeh{position:absolute;width:var(--bs);height:var(--bs);border-radius:50%;
    background:radial-gradient(circle,rgba(255,255,255,.9) 0%,rgba(255,210,230,.5) 35%,transparent 70%);
    filter:blur(4px);opacity:0;pointer-events:none;
    animation:bokehFloat var(--bt) ease-in-out var(--bd) infinite alternate}
  @keyframes bokehFloat{
    0%{opacity:.35;transform:translate(0,0) scale(1)}
    100%{opacity:.85;transform:translate(20px,-30px) scale(1.25)}}

  /* ═══ CURSOR-FOLLOWING GLOW ═══ */
  .cursor-glow{position:fixed;top:0;left:0;width:520px;height:520px;border-radius:50%;
    pointer-events:none;
    background:radial-gradient(circle,rgba(255,180,215,.35),rgba(150,180,255,.18) 45%,transparent 72%);
    filter:blur(30px);z-index:1;will-change:transform}

  /* ═══ TITLE GLOW PULSE ═══ */
  h1.love-title{
    animation:fadeInDown 1s cubic-bezier(.2,.8,.2,1) both,
              titleGlow 4s ease-in-out 1.2s infinite}
  @keyframes titleGlow{
    0%,100%{text-shadow:0 3px 14px rgba(11,46,26,.35),0 0 6px rgba(255,255,255,.6)}
    50%{text-shadow:0 3px 18px rgba(11,46,26,.5),0 0 26px rgba(255,200,220,.9),
        0 0 46px rgba(255,140,190,.55)}}

  /* ═══ SUBTLE 3D TILT ON CARDS ═══ */
  .tl-card{
    transition:transform .3s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease,border-color .35s ease;
    transform-style:preserve-3d}

  /* ═══ CONFETTI HEART KEYFRAMES ═══ */
  @keyframes confettiFloat{
    0%{opacity:1;transform:translate(-50%,-50%) scale(.8)}
    100%{opacity:0;
      transform:translate(calc(-50% + var(--dx)),calc(-50% + var(--dy))) scale(1.4) rotate(15deg)}}
  .bubble{position:absolute;bottom:-50px;width:var(--s);height:var(--s);border-radius:50%;
    background:radial-gradient(circle at 30% 28%,rgba(255,255,255,.95) 0%,rgba(255,255,255,.35) 28%,rgba(180,220,255,.20) 55%,rgba(255,255,255,.05) 100%);
    border:1px solid rgba(255,255,255,.55);
    box-shadow:inset -2px -3px 6px rgba(255,255,255,.55),inset 2px 2px 4px rgba(120,180,240,.35),0 0 10px rgba(255,255,255,.45);
    animation:rise var(--t) linear var(--d) infinite;opacity:0}
  @keyframes rise{0%{transform:translate3d(0,0,0) scale(.5);opacity:0}10%{opacity:.95}
    50%{transform:translate3d(calc(var(--x)*.6),-50vh,0) scale(1);opacity:.85}90%{opacity:.55}
    100%{transform:translate3d(var(--x),-110vh,0) scale(1.15);opacity:0}}
  .leaf{position:absolute;top:-50px;width:var(--s);height:calc(var(--s)*.6);
    background:linear-gradient(135deg,#a4e07a 0%,#4caf50 55%,#2e7d32 100%);border-radius:50% 0 50% 0;
    box-shadow:inset -1px -1px 3px rgba(0,0,0,.20),inset 1px 1px 2px rgba(255,255,255,.35),0 3px 6px rgba(0,0,0,.15);
    animation:fall-leaf var(--t) linear var(--d) infinite;opacity:0}
  @keyframes fall-leaf{0%{transform:translate3d(0,-10vh,0) rotate(0) rotateY(0);opacity:0}8%{opacity:.9}
    50%{transform:translate3d(calc(var(--x)*.5),50vh,0) rotate(360deg) rotateY(180deg)}90%{opacity:.75}
    100%{transform:translate3d(var(--x),115vh,0) rotate(720deg) rotateY(360deg);opacity:0}}
  .dot{position:absolute;width:var(--s);height:var(--s);border-radius:50%;background:#fff;
    box-shadow:0 0 5px rgba(255,255,255,.95),0 0 12px rgba(255,246,200,.85),0 0 22px rgba(255,240,180,.55);
    animation:twinkle var(--t) ease-in-out var(--d) infinite;opacity:0}
  @keyframes twinkle{0%,100%{opacity:0;transform:scale(.4)}50%{opacity:1;transform:scale(1.35)}}
  @keyframes fadeInDown{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:none}}
  @keyframes fadeInUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
  h1.love-title{font-family:'Great Vibes',cursive !important;text-align:center;font-size:5.5rem;
    font-weight:600;color:#0B2E1A;margin:0;-webkit-text-stroke:3px #fff;paint-order:stroke fill;
    text-shadow:0 3px 14px rgba(11,46,26,.35),0 0 6px rgba(255,255,255,.6);
    animation:fadeInDown 1s cubic-bezier(.2,.8,.2,1) both}
  p.love-sub{font-family:'Cormorant Garamond',serif !important;font-weight:800;font-style:italic;
    text-align:center;font-size:1.1rem;letter-spacing:.35em;text-transform:uppercase;color:#0B2E1A;
    margin:.9rem auto 0 auto;display:inline-block;padding:.35rem 1.2rem;border:2px solid #FFD6E8;
    border-radius:999px;background:rgba(255,255,255,.15);
    box-shadow:0 0 8px rgba(255,214,232,.9),0 0 1px rgba(255,255,255,.8) inset;
    animation:fadeInUp .9s .15s cubic-bezier(.2,.8,.2,1) both}
  .timeline{position:relative;max-width:920px;margin:10px auto 30px auto;padding:30px 0}
  .timeline::before{content:'';position:absolute;left:50%;top:0;bottom:0;width:4px;transform:translateX(-50%);
    border-radius:4px;background:linear-gradient(180deg,transparent 0%,#0B2E1A 8%,#c2185b 50%,#0B2E1A 92%,transparent 100%);
    box-shadow:0 0 12px rgba(194,24,91,.35)}
  .tl-item{position:relative;width:50%;padding:20px 60px;box-sizing:border-box;opacity:0;transform:translateY(28px);
    animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:var(--d)}
  .tl-item.left{left:0;text-align:right}.tl-item.right{left:50%;text-align:left}
  .tl-heart{position:absolute;top:28px;width:34px;height:34px;z-index:3;
    filter:drop-shadow(0 3px 8px rgba(11,46,26,.45));animation:beat 2.4s ease-in-out infinite}
  @keyframes beat{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
  .tl-item.left .tl-heart{right:-17px}.tl-item.right .tl-heart{left:-17px}
  .tl-heart svg{width:100%;height:100%}
  a.tl-card,a.tl-card:visited,a.tl-card:hover,a.tl-card:active{text-decoration:none;color:inherit}
  .tl-card{display:inline-block;padding:16px 24px;border-radius:18px;
    background:linear-gradient(135deg,#fdf7ff 0%,#f4e9fa 60%,#efe0f7 100%);border:2px solid #0B2E1A;
    box-shadow:0 10px 26px rgba(11,46,26,.28);
    transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s ease,border-color .35s ease;
    text-align:inherit;position:relative;overflow:hidden;cursor:pointer;min-width:240px;min-height:96px}
  .tl-card::before{content:'';position:absolute;inset:0;
    background:radial-gradient(circle at 15% 20%,rgba(200,150,230,.22) 0%,transparent 60%);pointer-events:none}
  .tl-card:hover{transform:translateY(-5px) scale(1.03);border-color:#c2185b;box-shadow:0 18px 38px rgba(11,46,26,.45)}
  .tl-content{display:block;transition:opacity .3s ease}.tl-card:hover .tl-content{opacity:0}
  .tl-hover-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.45rem;color:#7a0a1e;
    letter-spacing:.02em;-webkit-text-stroke:.6px #7a0a1e;opacity:0;transform:scale(.94);
    transition:opacity .3s ease,transform .3s ease;pointer-events:none;text-align:center;padding:0 12px}
  .tl-card:hover .tl-hover-text{opacity:1;transform:scale(1)}
  .tl-emoji{display:inline-block;font-size:1.15rem;margin-bottom:4px}
  .tl-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.45rem;color:#04160C;
    line-height:1.25;margin:2px 0 8px 0;-webkit-text-stroke:.6px #04160C}
  .tl-date{display:inline-block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;
    font-size:.85rem;letter-spacing:.22em;text-transform:uppercase;color:#4a0312;padding:3px 12px;
    border-radius:999px;background:#ffd9e8;border:1.5px solid #7a0a1e}
  .empty-state{max-width:640px;margin:40px auto;padding:50px 40px;border-radius:24px;
    background:linear-gradient(135deg,#fdf7ff 0%,#f0e6fa 100%);border:2px dashed #0B2E1A;
    box-shadow:0 14px 38px rgba(11,46,26,.28);text-align:center;
    animation:fadeInUp .9s cubic-bezier(.2,.8,.2,1) both}
  .empty-emoji{font-size:3rem;display:block;margin-bottom:12px;opacity:.75}
  .empty-title{font-family:'Great Vibes',cursive;font-size:2.4rem;color:#04160C;margin:0 0 10px 0}
  .empty-text{font-family:'Lora',serif;font-style:italic;font-size:1rem;color:#04160C;
    opacity:.75;line-height:1.7}
  .empty-hint{display:inline-block;margin-top:16px;font-family:'Inter',sans-serif;font-weight:600;
    font-size:.82rem;letter-spacing:.14em;text-transform:uppercase;color:#7a0a1e;
    padding:8px 18px;border-radius:999px;background:#ffd9e8;border:1.5px solid #7a0a1e}
  .no-photo{max-width:820px;margin:24px auto 22px auto;padding:56px 30px;
    border-radius:20px;text-align:center;
    background:linear-gradient(135deg,#fdf7ff 0%,#f0e6fa 100%);
    border:2px dashed #0B2E1A;box-shadow:0 12px 30px rgba(11,46,26,.22)}
  .no-photo-emoji{font-size:3rem;display:block;margin-bottom:10px;opacity:.55}
  .no-photo-text{font-family:'Lora',serif;font-style:italic;font-size:1rem;color:#04160C;opacity:.65}
  .ending-card{max-width:720px;margin:30px auto 20px auto;padding:34px 40px;border-radius:24px;
    background:linear-gradient(135deg,#fdf6ff 0%,#f0e6fa 55%,#e6e0f7 100%);border:2px dashed #0B2E1A;
    box-shadow:0 14px 38px rgba(11,46,26,.28);text-align:center;position:relative;overflow:hidden;
    animation:fadeInUp 1s .6s cubic-bezier(.2,.8,.2,1) both}
  .ending-card::before{content:'';position:absolute;inset:0;
    background:radial-gradient(circle at 50% 50%,rgba(200,150,230,.20) 0%,transparent 65%);
    pointer-events:none;animation:pulseGlow 4s ease-in-out infinite}
  @keyframes pulseGlow{0%,100%{opacity:.4}50%{opacity:1}}
  .ending-heart{font-size:2.2rem;display:block;margin-bottom:8px;animation:beat 2.4s ease-in-out infinite;
    filter:drop-shadow(0 0 12px rgba(255,92,138,.65))}
  .ending-title{font-family:'Great Vibes',cursive;font-size:2.6rem;color:#04160C;margin:4px 0 10px 0;
    text-shadow:0 2px 10px rgba(194,24,91,.35)}
  .ending-text{font-family:'Lora',serif;font-style:italic;font-weight:500;font-size:1.02rem;color:#04160C;
    opacity:.85;line-height:1.7;letter-spacing:.02em}
  .ending-dots{margin-top:16px;letter-spacing:1em;font-size:1.4rem;color:#c2185b;
    animation:fadeInOut 2.6s ease-in-out infinite}
  @keyframes fadeInOut{0%,100%{opacity:.4}50%{opacity:1}}
  .love-note{max-width:720px;margin:10px auto 70px auto;padding:30px 20px;text-align:center;
    animation:fadeInUp 1.2s .9s cubic-bezier(.2,.8,.2,1) both}
  .love-note-line{width:160px;height:2px;margin:0 auto;
    background:linear-gradient(90deg,transparent,#0B2E1A 40%,#0B2E1A 60%,transparent);
    border-radius:2px;opacity:.55}
  .love-note-text{font-family:'Dancing Script',cursive;font-weight:700;font-size:4.2rem;color:#c2185b;
    margin:14px 0 8px 0;line-height:1.15;letter-spacing:.01em;
    text-shadow:0 0 12px rgba(255,92,138,.45),0 3px 10px rgba(122,10,30,.35);
    -webkit-text-stroke:1.2px #fff;paint-order:stroke fill;animation:lovePulse 3s ease-in-out infinite}
  @keyframes lovePulse{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
  .love-note-sub{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;font-size:1.05rem;
    letter-spacing:.35em;text-transform:uppercase;color:#0B2E1A;opacity:.75;margin:0 0 18px 0}
  .detail-wrap{max-width:880px;margin:10px auto 40px auto;animation:fadeInUp .8s cubic-bezier(.2,.8,.2,1) both}
  .detail-hero{text-align:center;margin:10px 0 18px 0}
  .detail-emoji{font-size:3.4rem;display:block;margin-bottom:6px;filter:drop-shadow(0 4px 12px rgba(11,46,26,.35))}
  .detail-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:2.6rem;color:#04160C;
    margin:6px 0 12px 0;-webkit-text-stroke:.7px #04160C;line-height:1.15}
  .detail-date{display:inline-block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;
    font-size:.95rem;letter-spacing:.28em;text-transform:uppercase;color:#4a0312;padding:5px 18px;
    border-radius:999px;background:#ffd9e8;border:1.5px solid #7a0a1e}
  .gallery{display:grid;gap:14px;margin:24px auto 22px auto;max-width:820px;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
  .gallery img{width:100%;height:220px;object-fit:cover;border-radius:18px;border:3px solid #0B2E1A;
    box-shadow:0 14px 32px rgba(11,46,26,.32);
    transition:transform .4s cubic-bezier(.2,.8,.2,1),box-shadow .4s ease;cursor:pointer}
  .gallery img:hover{transform:translateY(-6px) scale(1.03);box-shadow:0 22px 48px rgba(11,46,26,.45)}
  .gallery img.single{grid-column:1/-1;height:auto;max-height:520px}
  .detail-about{max-width:820px;margin:0 auto;padding:26px 30px;border-radius:20px;
    background:linear-gradient(135deg,#fdf7ff 0%,#f4e9fa 60%,#efe0f7 100%);border:2px solid #0B2E1A;
    box-shadow:0 12px 30px rgba(11,46,26,.24);font-family:'Lora',serif;font-style:italic;font-weight:500;
    font-size:1.15rem;line-height:1.85;color:#04160C;position:relative;overflow:hidden}
  .detail-about::before{content:'';position:absolute;inset:0;
    background:radial-gradient(circle at 10% 10%,rgba(200,150,230,.18) 0%,transparent 55%);pointer-events:none}
  .detail-label{display:block;font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:700;
    font-size:.78rem;letter-spacing:.28em;text-transform:uppercase;color:#7a0a1e;margin-bottom:8px}
  .detail-empty-story{opacity:.55;font-style:italic}
  .stButton>button{background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%);
    border:2px solid #062b18;color:#f4fff8;font-family:'Inter',sans-serif;font-weight:600;letter-spacing:.04em;
    border-radius:999px;transition:all .3s cubic-bezier(.2,.8,.2,1);white-space:nowrap;
    text-shadow:0 1px 2px rgba(0,0,0,.35);
    box-shadow:0 8px 20px rgba(6,43,24,.42),inset 0 1px 2px rgba(255,255,255,.28)}
  .stButton>button:hover{background:linear-gradient(135deg,#14532d 0%,#237a4a 55%,#3ab877 100%);
    border-color:#1c6b3f;color:#fff;transform:translateY(-2px) scale(1.03);
    box-shadow:0 14px 30px rgba(6,43,24,.55),inset 0 1px 3px rgba(255,255,255,.45)}
  .stButton>button:active{transform:translateY(0) scale(.97)}
  .stButton>button p{color:#f4fff8 !important;font-weight:600 !important}
  .stButton>button[kind="secondary"]{padding:.38rem 1rem;font-size:.85rem}
  .stButton>button[kind="primary"]{background:linear-gradient(135deg,#5b0616 0%,#7a0a1e 45%,#c2185b 100%);
    border-color:#3a030e;padding:.38rem 1rem;font-size:.85rem}
  .stButton>button[kind="primary"]:hover{background:linear-gradient(135deg,#7a0a1e 0%,#a10a4a 45%,#e02a72 100%);border-color:#5b0616}
  .stTextInput input,.stTextArea textarea,.stDateInput input{
    background:linear-gradient(135deg,#fff0f6 0%,#ffe0ee 100%) !important;color:#4a0312 !important;
    border-radius:14px !important;border:2px solid #c2185b !important;font-family:'Lora',serif !important;
    font-weight:600 !important;font-size:1rem !important;
    box-shadow:inset 0 2px 6px rgba(194,24,91,.10),0 4px 10px rgba(194,24,91,.12) !important;
    transition:all .3s cubic-bezier(.2,.8,.2,1) !important}
  .stTextInput input:focus,.stTextArea textarea:focus,.stDateInput input:focus{
    border-color:#7a0a1e !important;
    box-shadow:0 0 0 3px rgba(194,24,91,.25),inset 0 2px 6px rgba(194,24,91,.10) !important;
    background:linear-gradient(135deg,#fff7fb 0%,#ffe8f2 100%) !important}
  .stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#b06b85 !important;font-style:italic !important}
  .stTextInput label,.stTextArea label,.stDateInput label,.stSelectbox label,
  .stFileUploader label,.stMultiSelect label{color:#0B2E1A !important;font-family:'Cormorant Garamond',serif !important;
    font-style:italic !important;font-weight:700 !important;letter-spacing:.15em !important;font-size:1.05rem !important}
  .stSelectbox div[data-baseweb="select"]>div,.stMultiSelect div[data-baseweb="select"]>div{
    background:linear-gradient(135deg,#fff0f6 0%,#ffe0ee 100%) !important;border:2px solid #c2185b !important;
    border-radius:14px !important;color:#4a0312 !important;font-family:'Lora',serif !important;
    font-weight:600 !important;box-shadow:inset 0 2px 6px rgba(194,24,91,.10),0 4px 10px rgba(194,24,91,.12) !important}
  .stFileUploader section{background:linear-gradient(135deg,#fff0f6 0%,#ffe0ee 100%) !important;
    border:2px dashed #c2185b !important;border-radius:16px !important;
    box-shadow:inset 0 2px 8px rgba(194,24,91,.10) !important;transition:all .3s ease !important}
  .stFileUploader section:hover{border-color:#7a0a1e !important;
    background:linear-gradient(135deg,#fff7fb 0%,#ffe8f2 100%) !important}
  section[data-testid="stFileUploadDropzone"]{color:#4a0312 !important}
  section[data-testid="stFileUploadDropzone"] button{
    background:linear-gradient(135deg,#0d3b25 0%,#1c6b3f 55%,#2e9e63 100%) !important;color:#f4fff8 !important;
    border:2px solid #062b18 !important;border-radius:999px !important;
    font-family:'Inter',sans-serif !important;font-weight:600 !important}
  .add-panel{max-width:720px;margin:10px auto 30px auto;padding:26px 30px;border-radius:22px;
    background:linear-gradient(135deg,#fdf7ff 0%,#f4e9fa 60%,#efe0f7 100%);border:2px solid #0B2E1A;
    box-shadow:0 14px 34px rgba(11,46,26,.3);animation:fadeInUp .7s cubic-bezier(.2,.8,.2,1) both}
  /* ── Unlock / Add / Edit panel headings: always very dark green-black ── */
  .add-title,
  .add-panel h2,
  .add-panel h2.add-title,
  h2.add-title,
  [data-testid="stMarkdownContainer"] h2.add-title,
  [data-testid="stMarkdownContainer"] .add-panel h2{
    font-family:'Great Vibes',cursive !important;
    font-size:2.6rem !important;
    font-weight:600 !important;
    text-align:center !important;
    margin:0 0 6px 0 !important;
    color:#04160C !important;
    -webkit-text-fill-color:#04160C !important;
    -webkit-text-stroke:0 !important;
    opacity:1 !important;
    filter:none !important;
    mix-blend-mode:normal !important;
    text-shadow:0 1px 0 rgba(255,255,255,.55);
  }
  .danger-box{max-width:720px;margin:16px auto;padding:22px 26px;border-radius:18px;
    background:linear-gradient(135deg,#fff0f6 0%,#ffe0ee 100%);border:2px dashed #c2185b;
    box-shadow:0 12px 30px rgba(194,24,91,.25);text-align:center;animation:fadeInUp .5s ease-out both}
  .danger-title{font-family:'Lora',serif;font-style:italic;font-weight:700;font-size:1.3rem;color:#7a0a1e;margin:0 0 6px 0}
  .danger-text{font-family:'Lora',serif;font-style:italic;color:#4a0312;font-size:.95rem}
  @media (max-width:680px){
    .timeline::before{left:22px}
    .tl-item{width:100%;left:0 !important;text-align:left !important;padding:18px 20px 18px 62px}
    .tl-item.left .tl-heart,.tl-item.right .tl-heart{left:5px;right:auto}
    .detail-title{font-size:2rem}.detail-about{font-size:1rem;padding:20px 22px}
    .tl-hover-text{font-size:1.2rem}.gallery{grid-template-columns:1fr}
    h1.love-title{font-size:3.6rem}
    .love-note-text{font-size:2.8rem}.love-note-sub{font-size:.85rem;letter-spacing:.25em}
    .add-title,[data-testid="stMarkdownContainer"] h2.add-title{font-size:2rem !important}}
</style>
""", unsafe_allow_html=True)

st.markdown(PARTICLES, unsafe_allow_html=True)
components.html("""<script>
(function(){
  const p = window.parent.document;

  /* ── Parallax on background layer ── */
  const bg = p.getElementById('living-bg');
  if (bg) {
    let r;
    function onScroll(){
      cancelAnimationFrame(r);
      r = requestAnimationFrame(() => {
        const y = p.documentElement.scrollTop || p.body.scrollTop || 0;
        bg.style.transform = 'translateY(' + (y * 0.35) + 'px)';
      });
    }
    p.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ── Cursor-following glow ── */
  const glow = p.getElementById('cursor-glow');
  if (glow) {
    let gx = 0, gy = 0, tx = 0, ty = 0;
    p.addEventListener('mousemove', e => { tx = e.clientX; ty = e.clientY; });
    (function anim(){
      gx += (tx - gx) * 0.12;
      gy += (ty - gy) * 0.12;
      glow.style.transform = `translate(${gx}px, ${gy}px) translate(-50%,-50%)`;
      requestAnimationFrame(anim);
    })();
  }

  /* ── 3D tilt on timeline cards ── */
  p.addEventListener('mousemove', e => {
    const card = e.target.closest && e.target.closest('.tl-card');
    if (!card) return;
    const rc = card.getBoundingClientRect();
    const x = (e.clientX - rc.left) / rc.width - 0.5;
    const y = (e.clientY - rc.top) / rc.height - 0.5;
    card.style.transform =
      `perspective(700px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateY(-5px) scale(1.03)`;
  });
  p.addEventListener('mouseout', e => {
    const card = e.target.closest && e.target.closest('.tl-card');
    if (card) card.style.transform = '';
  });

  /* ── Confetti hearts on click ── */
  p.addEventListener('click', e => {
    const t = e.target;
    if (t.closest('button, input, textarea, select, [data-testid="stFileUploaderDropzone"]')) return;
    const glyphs = ['❤️','💖','💕','💗','💘','🌸'];
    for (let i = 0; i < 5; i++) {
      const h = p.createElement('span');
      h.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
      h.style.cssText =
        'position:fixed;left:' + e.clientX + 'px;top:' + e.clientY + 'px;' +
        'font-size:' + (14 + Math.random() * 12) + 'px;pointer-events:none;z-index:99999;' +
        'animation:confettiFloat ' + (1 + Math.random() * 0.8) + 's ease-out forwards;' +
        'transform:translate(-50%,-50%);will-change:transform,opacity;';
      h.style.setProperty('--dx', (Math.random() - 0.5) * 220 + 'px');
      h.style.setProperty('--dy', -(60 + Math.random() * 120) + 'px');
      p.body.appendChild(h);
      setTimeout(() => h.remove(), 2200);
    }
  });

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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap');
  .counter-wrap{{display:flex;justify-content:center;padding:20px 0 6px 0;
    animation:fadeInUp 1s .3s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes fadeInUp{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:none}}}}
  .days-counter{{display:inline-flex;align-items:center;gap:14px;padding:14px 28px;border-radius:999px;
    background:rgba(255,255,255,.28);backdrop-filter:blur(14px) saturate(1.4);
    -webkit-backdrop-filter:blur(14px) saturate(1.4);border:1.5px solid rgba(255,255,255,.65);
    box-shadow:0 12px 34px rgba(11,46,26,.22),inset 0 1px 1px rgba(255,255,255,.85),
      inset 0 -1px 2px rgba(11,46,26,.08);font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
    font-style:normal;letter-spacing:.02em;color:#0B2E1A}}
  .counter-label{{font-weight:500;font-size:.82rem;letter-spacing:.22em;text-transform:uppercase;
    color:#0B2E1A;opacity:.7}}
  .counter-sep{{width:1.5px;height:26px;
    background:linear-gradient(180deg,transparent,rgba(11,46,26,.35),transparent)}}
  .counter-unit{{display:inline-flex;align-items:baseline;gap:5px}}
  .counter-unit b{{font-size:1.45rem;font-weight:700;color:#0B2E1A;line-height:1;
    font-variant-numeric:tabular-nums;text-shadow:0 1px 0 rgba(255,255,255,.6);min-width:2.6ch;text-align:right}}
  .counter-unit span{{font-size:.72rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
    color:#0B2E1A;opacity:.62}}
  @media(max-width:680px){{.days-counter{{gap:10px;padding:12px 18px}}
    .counter-unit b{{font-size:1.15rem}}.counter-unit span{{font-size:.65rem}}
    .counter-label{{font-size:.72rem}}}}
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

st.markdown('<hr style="border:none;height:2px;width:90%;margin:1rem auto;background:linear-gradient(90deg,transparent,#0B2E1A 15%,#0B2E1A 85%,transparent);border-radius:2px;opacity:.7">', unsafe_allow_html=True)

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
                if not title.strip():
                    st.warning("Please enter a title.")
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
        gal = ('<div class="no-photo">'
               '<span class="no-photo-emoji">📷</span>'
               '<div class="no-photo-text">No photos for this moment yet.</div>'
               '</div>')

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
        st.markdown("""
        <div class="empty-state">
          <span class="empty-emoji">🌱</span>
          <div class="empty-title">Our story is just beginning…</div>
          <div class="empty-text">
            No moments yet. Click <b>✚ Add Moment</b> in the top-right corner
            to write the very first page of our diary.
          </div>
          <div class="empty-hint">✚ Add Moment</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        items = "".join(
            f'<div class="tl-item {"left" if i%2==0 else "right"}" style="--d:{i*.12:.2f}s">'
            f'<div class="tl-heart"><svg viewBox="0 0 32 32"><defs>'
            f'<radialGradient id="hg{i}" cx="35%" cy="30%" r="75%">'
            f'<stop offset="0%" stop-color="#ffd0e0"/><stop offset="55%" stop-color="#c2185b"/>'
            f'<stop offset="100%" stop-color="#6b0f2e"/></radialGradient></defs>'
            f'<path d="{HEART}" fill="url(#hg{i})" stroke="#fff" stroke-width="2"/></svg></div>'
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
