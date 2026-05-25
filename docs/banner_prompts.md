# GhostFetch Banner Image Prompts

Use these prompts with high-end image generation models (Gemini/Banan Pro/GPT-Image-2, Midjourney, DALL-E 3, etc.) to generate a professional GitHub repo banner.

**Recommended specs:** 1280×640px (GitHub social preview) or 1792×1024 (wide aspect ratio).

---

## Prompt 1 — Full Detail (Best for GPT-Image-2 / Gemini)

```
A premium, dark-themed tech banner for an open-source developer tool called "GhostFetch". 
Dimensions: wide cinematic banner, 1280x640.

Visual composition:
- Deep charcoal background (#121212) with subtle radial gradient toward the center.
- A glowing geometric origami fox head (the "Phantom Fox" mascot) on the right side, 
  rendered in ghostly cyan (#00FFCC) with a lower half that dissolves into a digital mist 
  or ghost tail made of floating particles and network nodes.
- The fox has bright, piercing eyes and a sleek, minimalist angular design.
- Behind the fox, faint glowing cyan network nodes connected by thin lines form a web 
  or constellation pattern — representing the internet/web.
- On the left side, clean modern typography:
  Title: "GhostFetch" in large, bold, geometric sans-serif font (Inter or Geist style), 
  colored in crisp terminal white (#F8FAFC).
  Under the title, a thin horizontal cyan (#00FFCC) accent line.
  Subtitle/tagline below: "Fetch the unfetchable." in the same cyan color.
  Small descriptive text: "Stealthy headless browser service for AI agents."
- At the bottom, three elegant rounded pill/badges with thin borders:
  "👻 Ghost Protocol" | "📜 LLM-Native" | "🛡️ Anti-Bot Bypass"
- In the background, a shattered or cracked red shield (representing anti-bot protection) 
  dissolving into pixels near the center-right.
- The fox appears to be gliding through the web network holding or near a glowing 
  scroll or document block of clean Markdown text.

Color palette:
- Background: Deep charcoal #121212 to dark navy #1a1a2e
- Primary accent: Ghostly cyan #00FFCC
- Text: Terminal white #F8FAFC
- Secondary text: Slate gray #94A3B8
- Accent glow: Soft cyan bloom with 10% opacity

Style: 
- Clean, modern, minimal UI/UX aesthetic.
- Subtle bloom/glow effects on cyan elements.
- Crisp vector-like edges.
- Professional quality suitable for a GitHub repository banner.
- No clutter, no excessive detail. Focused and striking.
```

---

## Prompt 2 — Concise / Model-Friendly (Best for Midjourney / Banan Pro)

```
Wide cinematic banner 1280x640 for GitHub repo "GhostFetch" — a stealth headless browser tool. 

Dark charcoal background with subtle radial gradient. On the right: a glowing geometric 
origami fox head in neon cyan that dissolves into digital mist at the bottom. The fox has 
piercing white eyes and glides through a web of faint cyan network nodes. Behind it, a red 
anti-bot shield shatters into pixels. 

On the left: bold white sans-serif text "GhostFetch", thin cyan underline, cyan tagline 
"Fetch the unfetchable.", and three small rounded badges: "Ghost Protocol", "LLM-Native", 
"Anti-Bot Bypass". Clean, minimal, professional UI aesthetic with subtle glow effects. 
Color palette: charcoal, cyan #00FFCC, white, slate gray. No clutter, high contrast, 
crisp edges.
```

---

## Prompt 3 — Isometric / 3D Style (Best for Gemini with 3D control)

```
A wide 1280x640 banner in an isometric 3D style for a developer tool called "GhostFetch".

Scene: A dark, sleek digital landscape viewed from an isometric angle. The ground is a 
grid of faint cyan lines on deep charcoal (#121212). 

Main subject: A stylized 3D geometric fox (the "Phantom Fox") made of translucent cyan 
glass or light, with a tail that fades into floating pixels and digital particles. The fox 
is mid-leap, gliding through the air toward the right. Its eyes glow bright white.

Environment: Floating 3D blocks and nodes representing web pages and network connections, 
connected by thin glowing cyan lines. In the background, a large red shield with a "bot" 
icon is cracked and breaking apart into glowing fragments.

Foreground left: Large bold text "GhostFetch" in a clean modern geometric sans-serif font, 
white with slight cyan glow. Below it: "Fetch the unfetchable." in cyan. Three small 
pill-shaped badges at the bottom: "Ghost Protocol", "LLM-Native Markdown", "Anti-Bot Bypass".

Atmosphere: Dark, mysterious, cyberpunk-lite. Bloom and lens flare on bright cyan elements. 
Professional, clean, no text clutter. High quality, crisp, suitable for a premium open-source 
project banner.
```

---

## Prompt 4 — ASCII / Retro Terminal (Alternative style)

```
A wide 1280x640 banner with a retro-futuristic terminal aesthetic for "GhostFetch".

Background: Dark terminal screen (#0D1117) with subtle scanlines and a faint CRT glow at 
the edges.

Main graphic: A glowing ASCII-art style fox silhouette constructed from geometric cyan 
brackets, slashes, and unicode box-drawing characters. The fox appears to be "phasing" 
through a digital firewall represented by a shattered grid of red characters.

Text layout:
- Top-left: "GhostFetch" in a bold monospaced/blocky font, bright white.
- Under it: a blinking cursor followed by "Fetch the unfetchable._" in cyan.
- Bottom: three terminal-style badges: [Ghost Protocol] [LLM-Native] [Anti-Bot Bypass]

Style: Matrix-meets-minimalism. Green/cyan text on black. Subtle glitch effects on edges. 
Clean, hacker-aesthetic, but polished enough for a professional GitHub banner. No excessive 
noise.
```

---

## Style Reference Images (Optional)

If your image model supports reference images, you can use:

1. **OpenClaw's Lobster** — Shows how a quirky mascot builds community
2. **Go Gopher** — Simple, iconic, geometric animal mascot
3. **Rust Ferris** — Friendly, recognizable, clean lines
4. **Stripe's developer docs headers** — Professional dark UI aesthetic

---

## Post-Generation Tips

After generating, you may want to:

1. **Upscale** the image to 2560×1280 for retina displays.
2. **Compress** using TinyPNG or similar to keep file size under 500KB for fast GitHub loading.
3. **Check contrast** — ensure the text area (left side) has enough contrast against the background.
4. **Crop** if needed — some models add unwanted padding.

## Current Banner

The current banner was generated programmatically with Pillow (Python) and saved as:
- `docs/banner.png` — 1280×640, PNG format

Replace this file with your AI-generated version once you're happy with it.
