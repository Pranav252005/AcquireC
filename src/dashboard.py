"""FastAPI dashboard for lead tracking with CRM features."""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db, init_db
from src.models import Lead, OutreachStatus
from src.tracker import (
    add_lead_note,
    get_all_cities,
    get_city_summary,
    get_hot_leads,
    get_lead_detail,
    get_leads_by_stage,
    get_outreach_stats,
    update_lead_stage,
)

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure tables exist before first request."""
    init_db()
    yield


app = FastAPI(title="Client Acquisition Dashboard", lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _lead_status(lead: Lead) -> str:
    """Return the latest outreach status for a lead."""
    if not lead.outreaches:
        return "none"
    for o in reversed(lead.outreaches):
        if o.status != OutreachStatus.PENDING:
            return o.status.value
    return "pending"


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Dashboard homepage."""
    outreach_stats = get_outreach_stats(db)
    stats = {
        "total": db.query(Lead).count(),
        "contacted": outreach_stats.get("contacted", 0),
        "failed": outreach_stats.get("failed", 0),
        "responded": outreach_stats.get("responded", 0),
        "pending": outreach_stats.get("pending", 0),
        "hot": len(get_hot_leads(db, min_score=70, limit=1000)),
    }

    cities = get_all_cities(db)
    recent_leads = (
        db.query(Lead).order_by(Lead.created_at.desc()).limit(10).all()
    )
    for lead in recent_leads:
        lead.latest_status = _lead_status(lead)

    hot_leads = get_hot_leads(db, min_score=70, limit=5)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "stats": stats,
            "cities": cities,
            "recent_leads": recent_leads,
            "hot_leads": hot_leads,
        },
    )


@app.get("/leads", response_class=HTMLResponse)
def leads(
    request: Request,
    city: str = Query(""),
    status: str = Query(""),
    min_score: int = Query(0),
    stage: str = Query(""),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List leads with filters and pagination."""
    query = db.query(Lead)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    if min_score > 0:
        query = query.filter(Lead.lead_score >= min_score)

    total = query.count()
    offset = (page - 1) * per_page
    page_leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(per_page).all()

    filtered = []
    for lead in page_leads:
        lead.latest_status = _lead_status(lead)
        if status and lead.latest_status != status:
            continue
        if stage and (lead.kanban_stage or "cold") != stage:
            continue
        filtered.append(lead)

    return templates.TemplateResponse(
        request,
        "leads.html",
        {
            "leads": filtered,
            "city_filter": city,
            "status_filter": status,
            "stage_filter": stage,
            "min_score": min_score,
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )


@app.get("/leads/{lead_id}", response_class=HTMLResponse)
def lead_detail(request: Request, lead_id: int, db: Session = Depends(get_db)):
    """Show single lead details with full CRM data."""
    lead = get_lead_detail(db, lead_id)
    if not lead:
        return HTMLResponse("Lead not found", status_code=404)
    lead.latest_status = _lead_status(lead)
    return templates.TemplateResponse(
        request,
        "lead_detail.html",
        {
            "lead": lead,
            "outreaches": lead.outreaches,
            "notes": lead.notes,
            "follow_ups": lead.follow_ups,
        },
    )


@app.post("/leads/{lead_id}/note")
def add_note(lead_id: int, note_text: str = Form(...), db: Session = Depends(get_db)):
    """Add a note to a lead."""
    lead = get_lead_detail(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    add_lead_note(db, lead_id, note_text)
    return RedirectResponse(url=f"/leads/{lead_id}", status_code=303)


@app.post("/leads/{lead_id}/stage")
def update_stage(lead_id: int, stage: str = Form(...), db: Session = Depends(get_db)):
    """Update a lead's kanban stage."""
    lead = update_lead_stage(db, lead_id, stage)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return RedirectResponse(url=f"/leads/{lead_id}", status_code=303)


@app.get("/kanban", response_class=HTMLResponse)
def kanban_board(request: Request, city: str = Query(""), db: Session = Depends(get_db)):
    """Kanban board view of leads."""
    stages = ["cold", "pitched", "replied", "meeting", "closed", "lost"]
    columns = {}
    for stage in stages:
        leads_in_stage = get_leads_by_stage(db, stage, city=city or None)
        for lead in leads_in_stage:
            lead.latest_status = _lead_status(lead)
        columns[stage] = leads_in_stage

    return templates.TemplateResponse(
        request,
        "kanban.html",
        {
            "columns": columns,
            "stages": stages,
            "city_filter": city,
        },
    )


@app.get("/hot-leads", response_class=HTMLResponse)
def hot_leads_page(request: Request, db: Session = Depends(get_db)):
    """Dedicated hot leads page."""
    leads = get_hot_leads(db, min_score=70, limit=50)
    for lead in leads:
        lead.latest_status = _lead_status(lead)
    return templates.TemplateResponse(
        request,
        "hot_leads.html",
        {"leads": leads},
    )


@app.get("/cities/{city}", response_class=HTMLResponse)
def city_report(request: Request, city: str, db: Session = Depends(get_db)):
    """City-specific report with pie chart."""
    stats = get_city_summary(db, city)
    leads_in_city = (
        db.query(Lead).filter(Lead.city.ilike(city)).order_by(Lead.created_at.desc()).all()
    )
    for lead in leads_in_city:
        lead.latest_status = _lead_status(lead)

    return templates.TemplateResponse(
        request,
        "city_report.html",
        {
            "city": city,
            "stats": stats,
            "leads": leads_in_city,
        },
    )


@app.get("/api/stats")
def api_stats(db: Session = Depends(get_db)):
    """JSON stats endpoint for charts."""
    outreach_stats = get_outreach_stats(db)
    return {
        "total": db.query(Lead).count(),
        "contacted": outreach_stats.get("contacted", 0),
        "failed": outreach_stats.get("failed", 0),
        "responded": outreach_stats.get("responded", 0),
        "pending": outreach_stats.get("pending", 0),
        "hot": len(get_hot_leads(db, min_score=70, limit=1000)),
    }


@app.get("/api/kanban/stats")
def api_kanban_stats(db: Session = Depends(get_db)):
    """JSON kanban stage counts."""
    stages = ["cold", "pitched", "replied", "meeting", "closed", "lost"]
    return {stage: len(get_leads_by_stage(db, stage)) for stage in stages}


@app.get("/drafts", response_class=HTMLResponse)
def list_drafts(request: Request):
    """List all WhatsApp draft files."""
    settings = get_settings()
    drafts_dir = settings.whatsapp_drafts_path
    files = []
    if drafts_dir.exists():
        for f in sorted(drafts_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix == ".txt":
                stat = f.stat()
                files.append(
                    {
                        "name": f.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
    return templates.TemplateResponse(request, "drafts.html", {"files": files})


def _resolve_draft(filename: str) -> Path | None:
    """Validate and resolve a draft filename inside the drafts directory."""
    if ".." in filename or "/" in filename or "\\" in filename:
        return None
    if not filename.endswith(".txt"):
        return None
    settings = get_settings()
    drafts_dir = settings.whatsapp_drafts_path
    path = drafts_dir / filename
    if not path.exists():
        return None
    return path


@app.get("/drafts/{filename}", response_class=HTMLResponse)
def view_draft(request: Request, filename: str):
    """View and edit a draft file."""
    path = _resolve_draft(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Draft not found")
    content = path.read_text(encoding="utf-8")
    return templates.TemplateResponse(
        request,
        "draft_detail.html",
        {"filename": filename, "content": content},
    )


@app.post("/drafts/{filename}")
def save_draft(filename: str, content: str = Form(...)):
    """Save changes to a draft file."""
    path = _resolve_draft(filename)
    if not path:
        raise HTTPException(status_code=404, detail="Draft not found")
    path.write_text(content, encoding="utf-8")
    return RedirectResponse(url=f"/drafts/{filename}", status_code=303)


def run_dashboard() -> None:
    """Start the dashboard server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="127.0.0.1", port=settings.dashboard_port, log_level="info")
