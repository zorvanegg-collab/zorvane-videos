# Zorvane Daily: autonomous daily production runbook

Owner: Facundo (Uruguay, Spanish). Channel: YouTube "Zorvane Daily" (GTA 6 fan page, Shorts only). Goal: monetization. Budget 0. Everything legal, always credit sources. The owner will NOT log in to YouTube/Buffer anymore: decide by yourself, ask only for VERY important things (purchases, plan upgrades, legal risk, account/identity steps).

## 0. Setup in a fresh session (files do not persist)
- `git clone https://github.com/zorvanegg-collab/zorvane-videos` (repo = engine + state; temporary videos only while uploading).
- `pip install --break-system-packages kokoro-onnx skia-python soundfile numpy onnxruntime pillow` (check first with `pip list`).
- Kokoro model files into /home/claude/kokoro/: `kokoro-v1.0.int8.onnx` and `voices-v1.0.bin` from the GitHub release `thewh1teagle/kokoro-onnx` tag `model-files-v1.0` (github.com/.../releases/download/model-files-v1.0/...).
- Engine: `python3 engine/engine.py spec.json out.mp4` (specs: engine/specs/*.json, beats with text/say/widget/hit; widgets: bignum, bars, stats, list, cta, **photo**). Run in the background/with long timeout (~3-5 min per video; render 10 in sequence or 2 in parallel).
- Fonts are in /usr/share/fonts/truetype/google-fonts/ofl/ (anton, archivoblack).

## 1. Each day: research (WebSearch/WebFetch)
- Topics: first ALL big GTA VI topics; only afterwards finer ones (easter eggs, interviews, trivia, reactions, rankings, comparisons to GTA V). Check engine/state/log.md and engine/state/topics_done.md to avoid repeating. Look for NEW news every day (Rockstar official, reviews, patches, updates, sales, community finds).
- Facts: official Rockstar info, or confirmed by several independent outlets (label "per previews/reports"); leaks/rumors = unconfirmed label or skip. Add every fact with its source to engine/state/facts.md BEFORE it appears on screen.
- Quality must improve every day: sharper hook in the first second, one idea per screen, more real analysis (what it means for the player, vs GTA V), better pacing/variation. Read engine/state/learning.md (YouTube Studio numbers if readable) and double down on formats that win.
- Rotate formats and palettes (sunset/night/dawn/toxic/ember): key dates, GTA5 vs GTA6, myth vs fact, top 3, "did you notice", guide, poll, timeline. Never the same template twice in a row (YouTube "inauthentic content" rule). 13-25 s each.

## 2. Images (legal only)
- NEVER use Rockstar/GTA footage or screenshots/trailer frames/press images: they are copyrighted, Rockstar's policy is non-commercial only and this channel is monetized.
- Use only license-clear images: Wikimedia Commons (CC BY / CC BY-SA / CC0 / public domain; real-world places such as Miami, Florida, cars, music artists, etc. when relevant), the own generated vector scenes, and Luanti footage. Download via the Wikimedia API (commons.wikimedia.org) when reachable, check the license field, and put the exact credit on screen through the `photo` widget: `["photo", {"file": "path.jpg", "credit": "Photo: Author / Wikimedia Commons / CC BY-SA 4.0"}]`. Put the same credit in the description. If a photo's license is unclear, do not use it. If the network blocks the download, skip photos for that video.
- Optionally use official Rockstar images ONLY if Rockstar publishes a license that allows commercial/fan use (check the official policy page first; currently it does not).

## 3. Every video must have
- Source line on screen (spec "source") and the on-screen fan-page disclaimer (the engine adds "Fan page. Not affiliated with Rockstar Games or Take-Two. AI narration."). Rumors labeled "reported"/"unconfirmed".
- Title <=100 chars ending with `#GTA6 #Shorts`; description = 1-2 sentence summary + `Source: ...` + `Fan page. Not affiliated with Rockstar Games or Take-Two.` + photo credits + `Narration: AI voice. #GTA6 #GTAVI #Shorts`.
- Loudness ~ -14 LUFS (engine does it). Output 1080x1920, h264+aac.

## 4. Daily output: 10 new videos
- Name them `bNN.mp4` unique per day (e.g. d20261120_01.mp4). Keep titles/descriptions in engine/state/schedule_YYYY-MM-DD.csv. Update engine/state/topics_done.md and engine/state/log.md. Commit engine/ changes to the repo (git push).

## 5. Buffer queue (browser pane tab "seed", Claude_Browser tools; read the built-in-browser skill first)
- Buffer free plan: max 10 queued posts. YouTube allows only a limited number of uploads per rolling 24 h; Buffer shows "Error: The daily posting limit ... reached" + "Retry Now" when YouTube refuses. So: ALWAYS keep the Buffer queue full (10) and let freed slots be filled; an hourly scheduled task retries failed posts ("Cola Zorvane...").
- Queue URL: https://publish.buffer.com/channels/6afdb706ece6dfde5f0bdb90/schedule?tab=queue (mobile layout, viewport 800x1143). Count pending posts; for each free slot, add one post:
  1. Push the mp4 to the repo (git add/commit/push; files must be on https://raw.githubusercontent.com/zorvanegg-collab/zorvane-videos/main/NAME).
  2. In Buffer, click the green + (752,124 without banner; ~(752,222-236) with the "posts left" banner), open composer.
  3. javascript_tool: `window.__inj = async (name)=>{const r=await fetch('https://raw.githubusercontent.com/zorvanegg-collab/zorvane-videos/main/'+name);const b=await r.blob();const f=new File([b],name,{type:'video/mp4'});const i=document.querySelector('input[type=file]');const dt=new DataTransfer();dt.items.add(f);i.files=dt.files;i.dispatchEvent(new Event('change',{bubbles:true}));return b.size}` then `await window.__inj('NAME')` (redefine after any page reload; composer must be open).
  4. Click description (400,318), type description; Title field below (y~732 with 3-line description, ~762 with 4 lines; screenshot to check), type title. Schedule via dropdown (340,1096) -> "Set Date and Time" -> pick the next free time (tomorrow/today a few hours ahead is fine; Buffer tries at that time; retry task handles errors) -> Done -> Schedule.
  5. Buffer validation "max 5 YouTube posts per day" can block saving when many posts share a day: spread the posts across different days/times, or use Move to Drafts -> Drafts tab (?tab=drafts) -> Schedule Post -> confirm popover.
- AFTER a post is scheduled/queued: delete its mp4 from the repo (git rm, commit, push) so the repo stays clean. Buffer already has its own copy.
- Do not delete/edit posts that already exist unless they are duplicates or broken.

## 6. Reporting
- Send Facundo (Spanish, 3-5 lines) a short summary per run: topics made, what is in the queue, any problem. Do not spam; ask only for VERY important decisions.
