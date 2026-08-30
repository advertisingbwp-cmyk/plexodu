import os
from pathlib import Path
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["public"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/")
async def public_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/blog")
async def public_blog(request: Request):
    return templates.TemplateResponse(request=request, name="blog/index.html")

@router.get("/blog/{slug}")
async def public_blog_post(request: Request, slug: str):
    return templates.TemplateResponse(request=request, name="blog/post.html", context={"slug": slug})

@router.get("/youtube-seo-tool")
async def seo_tool(request: Request):
    return templates.TemplateResponse(request=request, name="tools/youtube-seo-tool.html")

@router.get("/youtube-keyword-tool")
async def keyword_tool(request: Request):
    return templates.TemplateResponse(request=request, name="tools/youtube-keyword-tool.html")

@router.get("/youtube-trend-analyzer")
async def trend_analyzer(request: Request):
    return templates.TemplateResponse(request=request, name="tools/youtube-trend-analyzer.html")

@router.get("/youtube-competitor-analysis")
async def competitor_analysis(request: Request):
    return templates.TemplateResponse(request=request, name="tools/youtube-competitor-analysis.html")

@router.get("/youtube-video-analyzer")
async def video_analyzer(request: Request):
    return templates.TemplateResponse(request=request, name="tools/youtube-video-analyzer.html")

@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request=request, name="legal/privacy.html")

@router.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse(request=request, name="legal/terms.html")

@router.get("/sitemap.xml")
async def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://plexudo.vercel.app/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/youtube-seo-tool</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/youtube-video-analyzer</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/youtube-keyword-tool</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/youtube-trend-analyzer</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/youtube-competitor-analysis</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/blog</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/blog/mastering-youtube-seo-2026</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/blog/high-retention-hooks-first-15-seconds</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/privacy</loc>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
  <url>
    <loc>https://plexudo.vercel.app/terms</loc>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>"""
    return Response(content=xml_content.strip(), media_type="application/xml")

@router.get("/robots.txt")
async def robots():
    robots_txt = """User-agent: *
Allow: /
Allow: /blog
Allow: /blog/*
Allow: /youtube-seo-tool
Allow: /youtube-keyword-tool
Allow: /youtube-trend-analyzer
Allow: /youtube-competitor-analysis
Allow: /youtube-video-analyzer
Allow: /privacy
Allow: /terms

Disallow: /dashboard
Disallow: /settings
Disallow: /profile
Disallow: /history
Disallow: /tools/
Disallow: /api/

Sitemap: https://plexudo.vercel.app/sitemap.xml
"""
    return Response(content=robots_txt.strip(), media_type="text/plain")

@router.get("/favicon.ico")
async def favicon():
    svg_favicon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#4f46e5"/><text x="16" y="22" font-family="system-ui, sans-serif" font-weight="900" font-size="18" fill="white" text-anchor="middle">P</text></svg>"""
    return Response(content=svg_favicon, media_type="image/svg+xml")

from fastapi.responses import RedirectResponse
from app.core.config import get_settings

settings = get_settings()

@router.get("/login")
async def redirect_login():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/login")

@router.get("/signup")
async def redirect_signup():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/signup")

@router.get("/dashboard")
async def redirect_dashboard():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")

@router.get("/history")
async def redirect_history():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/history")

@router.get("/profile")
async def redirect_profile():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/profile")

@router.get("/settings")
async def redirect_settings():
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings")

