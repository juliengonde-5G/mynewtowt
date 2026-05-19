"""Claims module router — declaration, tracking, documents, timeline, SOF, PDF generation."""
import secrets, os
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.activity import log_activity, get_client_ip
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.templating import templates
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.vessel import Vessel
from app.models.leg import Leg
from app.models.order import OrderAssignment, Order
from app.models.crew import CrewMember
from app.models.onboard import SofEvent
from app.utils.timezones import TIMEZONE_CHOICES
from app.models.finance import LegFinance, InsuranceContract
from app.models.claim import (
    Claim, ClaimDocument, ClaimTimeline,
    CLAIM_TYPES, CLAIM_STATUSES, CLAIM_GUARANTEES, CLAIM_CONTEXTS,
    CLAIM_DOC_TYPES, CLAIM_RESPONSIBILITY, TIMELINE_ACTION_TYPES,
)

router = APIRouter(prefix="/claims", tags=["claims"])
UPLOAD_DIR = "/app/data/claims"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _gen_claim_ref(claim_type):
    prefix = {"cargo": "CRG", "crew": "CRW", "hull": "HUL"}.get(claim_type, "CLM")
    return f"CLM-{prefix}-{date.today().strftime('%y%m')}-{secrets.token_hex(2).upper()}"

def _pf(v):
    if not v or (isinstance(v, str) and not v.strip()): return None
    try: return float(str(v).replace(" ","").replace("\u00a0","").replace(",","."))
    except: return None

def _to_int(v):
    if not v or (isinstance(v, str) and not v.strip()): return None
    try: return int(v)
    except: return None

async def _save_upload(upload, claim_ref, prefix=""):
    if not upload or not upload.filename: return None, None
    # S7b: strip any directory components from the client-supplied filename
    safe_ref = os.path.basename(claim_ref) or "unknown"
    safe_name = os.path.basename(upload.filename)
    # S22: validate magic bytes + MIME
    from app.utils.file_validation import validate_upload, MAX_UPLOAD_SIZE_MB
    data = await upload.read()
    if len(data) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Fichier trop volumineux (>{MAX_UPLOAD_SIZE_MB}MB)")
    ok, err = validate_upload(safe_name, data)
    if not ok:
        raise HTTPException(400, err)
    d = os.path.join(UPLOAD_DIR, safe_ref); os.makedirs(d, exist_ok=True)
    name = f"{prefix}{secrets.token_hex(4)}_{safe_name}"
    path = os.path.join(d, name)
    with open(path, "wb") as f: f.write(data)
    return safe_name, path

# === LIST ===
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def claim_list(request: Request, claim_type: Optional[str]=Query(None), status: Optional[str]=Query(None), vessel: Optional[int]=Query(None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    query = select(Claim).options(selectinload(Claim.vessel), selectinload(Claim.leg).selectinload(Leg.departure_port), selectinload(Claim.leg).selectinload(Leg.arrival_port), selectinload(Claim.order_assignment).selectinload(OrderAssignment.order), selectinload(Claim.crew_member)).order_by(Claim.created_at.desc())
    if claim_type: query = query.where(Claim.claim_type == claim_type)
    if status: query = query.where(Claim.status == status)
    if vessel:
        vr = await db.execute(select(Vessel).where(Vessel.code == vessel))
        vo = vr.scalar_one_or_none()
        if vo: query = query.where(Claim.vessel_id == vo.id)
    result = await db.execute(query)
    claims = result.scalars().all()
    stats = {"total": len(claims), "open": sum(1 for c in claims if c.status=="open"), "declared": sum(1 for c in claims if c.status=="declared"), "instruction": sum(1 for c in claims if c.status=="instruction"), "closed": sum(1 for c in claims if c.status in ("accepted","refused","closed"))}
    total_provision = sum(float(c.provision_amount or 0) for c in claims if c.status not in ("closed","refused"))
    total_company = sum(float(c.company_charge or 0) for c in claims)
    vessels_result = await db.execute(select(Vessel).where(Vessel.is_active==True).order_by(Vessel.code))
    vessels = vessels_result.scalars().all()
    gantt_data = [{"id":c.id,"ref":c.reference,"type":c.claim_type,"status":c.status,"vessel":c.vessel.name if c.vessel else "","start":c.created_at.strftime("%Y-%m-%d") if c.created_at else "","end":c.closed_at.strftime("%Y-%m-%d") if c.closed_at else date.today().strftime("%Y-%m-%d"),"provision":float(c.provision_amount or 0)} for c in claims]
    return templates.TemplateResponse("claims/index.html", {"request":request,"user":user,"claims":claims,"stats":stats,"total_provision":total_provision,"total_company":total_company,"vessels":vessels,"gantt_data":gantt_data,"selected_type":claim_type,"selected_status":status,"selected_vessel":vessel,"claim_types":CLAIM_TYPES,"claim_statuses":CLAIM_STATUSES,"active_module":"claims"})

# === CREATE ===
@router.get("/create", response_class=HTMLResponse)
async def claim_create_form(request: Request, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    vessels = (await db.execute(select(Vessel).where(Vessel.is_active==True).order_by(Vessel.code))).scalars().all()
    legs = (await db.execute(select(Leg).options(selectinload(Leg.departure_port),selectinload(Leg.arrival_port),selectinload(Leg.vessel)).where(Leg.status!="cancelled").order_by(Leg.year.desc(),Leg.vessel_id,Leg.sequence))).scalars().all()
    oas = (await db.execute(select(OrderAssignment).options(selectinload(OrderAssignment.order),selectinload(OrderAssignment.leg)).order_by(OrderAssignment.id.desc()))).scalars().all()
    crew = (await db.execute(select(CrewMember).where(CrewMember.is_active==True).order_by(CrewMember.last_name))).scalars().all()
    return templates.TemplateResponse("claims/form.html", {"request":request,"user":user,"claim":None,"vessels":vessels,"legs":legs,"order_assignments":oas,"crew_members":crew,"claim_types":CLAIM_TYPES,"claim_contexts":CLAIM_CONTEXTS,"claim_guarantees":CLAIM_GUARANTEES,"claim_responsibility":CLAIM_RESPONSIBILITY,"tz_choices":TIMEZONE_CHOICES,"active_module":"claims"})

@router.post("/create", response_class=HTMLResponse)
async def claim_create_submit(request: Request, claim_type:str=Form(...), vessel_id:int=Form(...), leg_id:int=Form(...), context:str=Form(""), incident_date:str=Form(""), incident_location:str=Form(""), description:str=Form(...), guarantee_type:str=Form(""), responsibility:str=Form("pending"), provision_amount:str=Form(""), franchise_amount:str=Form(""), order_assignment_id:Optional[str]=Form(None), crew_member_id:Optional[str]=Form(None), notes:str=Form(""), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    ref = _gen_claim_ref(claim_type)
    inc_date = None
    if incident_date:
        try: inc_date = datetime.fromisoformat(incident_date)
        except: pass
    if not guarantee_type: guarantee_type = {"cargo":"pi","crew":"pi","hull":"hull_div"}.get(claim_type,"")
    # Auto-retrieve cargo zone from stowage plan for cargo claims
    cargo_zone = None
    if claim_type == "cargo" and _to_int(order_assignment_id):
        try:
            from app.models.stowage import StowagePlan
            from app.models.packing_list import PackingList as _PL, PackingListBatch as _PLB
            oa_r = await db.execute(select(OrderAssignment).where(OrderAssignment.id == _to_int(order_assignment_id)))
            oa = oa_r.scalar_one_or_none()
            if oa:
                pl_r = await db.execute(select(_PL).where(_PL.order_id == oa.order_id))
                pl = pl_r.scalar_one_or_none()
                if pl:
                    b_r = await db.execute(select(_PLB).where(_PLB.packing_list_id == pl.id))
                    for batch in b_r.scalars().all():
                        sp_r = await db.execute(select(StowagePlan).where(StowagePlan.leg_id == leg_id, StowagePlan.batch_id == batch.id))
                        sp = sp_r.scalar_one_or_none()
                        if sp:
                            cargo_zone = sp.zone_code
                            break
        except Exception:
            pass
    claim = Claim(reference=ref, claim_type=claim_type, status="open", vessel_id=vessel_id, leg_id=leg_id, order_assignment_id=_to_int(order_assignment_id) if claim_type=="cargo" else None, crew_member_id=_to_int(crew_member_id) if claim_type=="crew" else None, context=context or None, incident_date=inc_date, incident_location=incident_location or None, description=description, guarantee_type=guarantee_type or None, responsibility=responsibility, provision_amount=_pf(provision_amount), franchise_amount=_pf(franchise_amount), declared_by=user.full_name, notes=notes or None, cargo_zone=cargo_zone)
    db.add(claim); await db.flush()
    await log_activity(db, user=user, action="create", module="claims",
                       entity_type="claim", entity_id=claim.id,
                       entity_label=claim.reference,
                       ip_address=get_client_ip(request))
    db.add(ClaimTimeline(claim_id=claim.id, action_type="status_change", title="Claim ouvert", description=f"Claim {ref} ({claim.type_label}) créé", new_value="open", actor=user.full_name, action_date=datetime.now()))
    leg = await db.get(Leg, leg_id)
    if leg:
        sof = SofEvent(leg_id=leg_id, event_type="CLAIM_DECLARED", event_label=f"⚠️ Claim {ref} — {claim.type_label}", event_date=inc_date.date() if inc_date else date.today(), event_time=inc_date.strftime("%H:%M") if inc_date else datetime.now().strftime("%H:%M"), remarks=f"Claim {ref} ouvert : {description[:200]}", created_by=user.full_name)
        db.add(sof); await db.flush(); claim.sof_event_id = sof.id
    # Dashboard notification
    from app.models.notification import Notification
    vessel = await db.get(Vessel, vessel_id)
    vessel_name = vessel.name if vessel else "—"
    leg_code = leg.leg_code if leg else "—"
    db.add(Notification(type="new_claim", title=f"Claim {ref} ouvert — {claim.type_label} ({vessel_name})", detail=f"Voyage {leg_code} · {description[:150]}", link=f"/claims/{claim.id}", leg_id=leg_id))
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim.id}", status_code=303)

# === DETAIL ===
@router.get("/{claim_id}", response_class=HTMLResponse)
async def claim_detail(claim_id:int, request:Request, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Claim).options(selectinload(Claim.vessel),selectinload(Claim.leg).selectinload(Leg.departure_port),selectinload(Claim.leg).selectinload(Leg.arrival_port),selectinload(Claim.order_assignment).selectinload(OrderAssignment.order),selectinload(Claim.crew_member),selectinload(Claim.documents),selectinload(Claim.timeline),selectinload(Claim.sof_event)).where(Claim.id==claim_id))
    claim = result.scalar_one_or_none()
    if not claim: raise HTTPException(404)
    insurance = None
    if claim.guarantee_type:
        ir = await db.execute(select(InsuranceContract).where(InsuranceContract.guarantee_type==claim.guarantee_type, InsuranceContract.is_active==True))
        insurance = ir.scalar_one_or_none()
    return templates.TemplateResponse("claims/detail.html", {"request":request,"user":user,"claim":claim,"insurance":insurance,"claim_statuses":CLAIM_STATUSES,"claim_guarantees":CLAIM_GUARANTEES,"claim_responsibility":CLAIM_RESPONSIBILITY,"claim_doc_types":CLAIM_DOC_TYPES,"timeline_action_types":TIMELINE_ACTION_TYPES,"active_module":"claims"})

# === STATUS ===
@router.post("/{claim_id}/status", response_class=HTMLResponse)
async def claim_update_status(claim_id:int, request:Request, status:str=Form(...), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim: raise HTTPException(404)
    old = claim.status; claim.status = status
    if status == "closed": claim.closed_at = datetime.now()
    db.add(ClaimTimeline(claim_id=claim_id, action_type="status_change", title=f"Statut → {dict(CLAIM_STATUSES).get(status,status)}", old_value=old, new_value=status, actor=user.full_name, action_date=datetime.now()))
    if status == "declared" and old == "open":
        db.add(SofEvent(leg_id=claim.leg_id, event_type="CLAIM_DECLARED", event_label=f"📋 Claim {claim.reference} déclaré assureur", event_date=date.today(), event_time=datetime.now().strftime("%H:%M"), remarks=f"Claim {claim.reference} déclaré — Garantie {claim.guarantee_label}", created_by=user.full_name))
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)

# === FINANCE ===
@router.post("/{claim_id}/finance", response_class=HTMLResponse)
async def claim_update_finance(claim_id:int, request:Request, provision_amount:str=Form(""), franchise_amount:str=Form(""), indemnity_amount:str=Form(""), company_charge:str=Form(""), auto_compute:Optional[str]=Form(None), responsibility:str=Form("pending"), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim: raise HTTPException(404)
    prov=_pf(provision_amount); fran=_pf(franchise_amount); indem=_pf(indemnity_amount); comp=_pf(company_charge)
    if auto_compute == "on" or (comp is None and prov is not None):
        comp = max(0, (prov or 0) - (fran or 0) - (indem or 0))
    claim.provision_amount=prov; claim.franchise_amount=fran; claim.indemnity_amount=indem; claim.company_charge=comp; claim.responsibility=responsibility
    db.add(ClaimTimeline(claim_id=claim_id, action_type="financial_update", title="Mise à jour financière", description=f"Provision: {prov or 0:.2f}€ | Franchise: {fran or 0:.2f}€ | Prise en charge: {indem or 0:.2f}€ | Reste à charge: {comp or 0:.2f}€", actor=user.full_name, action_date=datetime.now()))
    if claim.responsibility == "company" and comp:
        cr = await db.execute(select(func.sum(Claim.company_charge)).where(Claim.leg_id==claim.leg_id, Claim.responsibility=="company", Claim.company_charge!=None))
        tc = float(cr.scalar() or 0)
        lfr = await db.execute(select(LegFinance).where(LegFinance.leg_id==claim.leg_id))
        lf = lfr.scalar_one_or_none()
        if lf: lf.claims_cost = tc
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim_id}#finance", status_code=303)

# === TIMELINE (with upload) ===
@router.post("/{claim_id}/timeline", response_class=HTMLResponse)
async def claim_add_timeline(claim_id:int, request:Request, action_type:str=Form(...), title:str=Form(...), description:str=Form(""), action_date:str=Form(""), attachment:Optional[UploadFile]=File(None), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim: raise HTTPException(404)
    try: ad = datetime.fromisoformat(action_date) if action_date else datetime.now()
    except: ad = datetime.now()
    fname, fpath = await _save_upload(attachment, claim.reference, "tl_") if attachment else (None, None)
    db.add(ClaimTimeline(claim_id=claim_id, action_type=action_type, title=title, description=description or None, filename=fname, file_path=fpath, actor=user.full_name, action_date=ad))
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim_id}#timeline", status_code=303)

# === DOCUMENTS (with upload) ===
@router.post("/{claim_id}/document", response_class=HTMLResponse)
async def claim_add_document(claim_id:int, request:Request, doc_type:str=Form(...), title:str=Form(...), notes:str=Form(""), file:Optional[UploadFile]=File(None), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim: raise HTTPException(404)
    fname, fpath = await _save_upload(file, claim.reference, "doc_") if file else (None, None)
    db.add(ClaimDocument(claim_id=claim_id, doc_type=doc_type, title=title, filename=fname, file_path=fpath, notes=notes or None, uploaded_by=user.full_name))
    db.add(ClaimTimeline(claim_id=claim_id, action_type="document_added", title=f"Document : {title}", description=f"Type: {dict(CLAIM_DOC_TYPES).get(doc_type,doc_type)}" + (f" — {fname}" if fname else ""), actor=user.full_name, action_date=datetime.now()))
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim_id}#documents", status_code=303)

@router.get("/{claim_id}/document/{doc_id}/download")
async def claim_download_doc(claim_id:int, doc_id:int, db:AsyncSession=Depends(get_db)):
    doc = await db.get(ClaimDocument, doc_id)
    if not doc or doc.claim_id!=claim_id: raise HTTPException(404)
    from app.utils.safe_files import safe_file_response
    return safe_file_response(doc.file_path, filename=doc.filename or "document")

@router.get("/{claim_id}/timeline/{tl_id}/download")
async def claim_download_tl(claim_id:int, tl_id:int, db:AsyncSession=Depends(get_db)):
    tl = await db.get(ClaimTimeline, tl_id)
    if not tl or tl.claim_id!=claim_id: raise HTTPException(404)
    from app.utils.safe_files import safe_file_response
    return safe_file_response(tl.file_path, filename=tl.filename or "document")

@router.delete("/{claim_id}/document/{doc_id}", response_class=HTMLResponse)
async def claim_delete_doc(claim_id:int, doc_id:int, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    doc = await db.get(ClaimDocument, doc_id)
    if doc and doc.claim_id==claim_id:
        if doc.file_path and os.path.exists(doc.file_path): os.remove(doc.file_path)
        await db.delete(doc); await db.flush()
    return HTMLResponse("", status_code=200)

# === GUARANTEE ===
@router.post("/{claim_id}/guarantee", response_class=HTMLResponse)
async def claim_update_guarantee(claim_id:int, request:Request, guarantee_type:str=Form(...), user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim: raise HTTPException(404)
    old = claim.guarantee_type; claim.guarantee_type = guarantee_type
    db.add(ClaimTimeline(claim_id=claim_id, action_type="note", title=f"Garantie → {dict(CLAIM_GUARANTEES).get(guarantee_type,guarantee_type)}", old_value=old, new_value=guarantee_type, actor=user.full_name, action_date=datetime.now()))
    await db.flush()
    return RedirectResponse(url=f"/claims/{claim_id}", status_code=303)

# === PDF DECLARATION ===
@router.get("/{claim_id}/declaration/pdf")
async def claim_declaration_pdf(claim_id:int, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Claim).options(selectinload(Claim.vessel),selectinload(Claim.leg).selectinload(Leg.departure_port),selectinload(Claim.leg).selectinload(Leg.arrival_port),selectinload(Claim.order_assignment).selectinload(OrderAssignment.order),selectinload(Claim.crew_member),selectinload(Claim.documents)).where(Claim.id==claim_id))
    claim = result.scalar_one_or_none()
    if not claim: raise HTTPException(404)
    insurance = None
    if claim.guarantee_type:
        ir = await db.execute(select(InsuranceContract).where(InsuranceContract.guarantee_type==claim.guarantee_type, InsuranceContract.is_active==True))
        insurance = ir.scalar_one_or_none()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT

    pdf_path = os.path.join(UPLOAD_DIR, f"declaration_{claim.reference}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    ts = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#095561'), spaceAfter=6)
    ss = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=12)
    hs = ParagraphStyle('H', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#095561'), spaceBefore=14, spaceAfter=6)
    bs = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, spaceAfter=4, leading=14)
    xs = ParagraphStyle('X', parent=styles['Normal'], fontSize=8, textColor=colors.gray)
    rs = ParagraphStyle('R', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT)
    story = []
    story.append(Paragraph("TOWT — Transport à la Voile", ts))
    story.append(Paragraph("Déclaration de sinistre", ss))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#095561')))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Date : {date.today().strftime('%d/%m/%Y')}", rs))
    story.append(Paragraph(f"Réf. Claim : <b>{claim.reference}</b>", bs))
    story.append(Spacer(1, 8))
    if insurance:
        story.append(Paragraph("Destinataire :", hs))
        t = Table([[f"Assureur : {insurance.insurer_name}", f"Garantie : {claim.guarantee_label}"],[f"Email : {insurance.insurer_email or '—'}", f"Tél : {insurance.insurer_phone or '—'}"],[f"Adresse : {insurance.insurer_address or '—'}", f"Courtier : {insurance.broker_reference or '—'}"]], colWidths=[250,220])
        t.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        story.append(t); story.append(Spacer(1,8))
    story.append(Paragraph("Détails du sinistre", hs))
    dd = [["Type",claim.type_label],["Navire",claim.vessel.name],["Voyage",f"{claim.leg.leg_code} — {claim.leg.departure_port.name} → {claim.leg.arrival_port.name}"],["Contexte",claim.context_label],["Date incident",claim.incident_date.strftime('%d/%m/%Y %H:%M') if claim.incident_date else "—"],["Lieu",claim.incident_location or "—"],["Provision",f"{float(claim.provision_amount or 0):,.2f} €"]]
    if claim.claim_type=="cargo" and claim.order_assignment:
        o = claim.order_assignment.order
        dd += [["",""],["MARCHANDISE",""],["Client / Chargeur",o.client_name],["Réf. commande",o.reference],["Description",o.description or "—"],["Quantité",f"{o.quantity_palettes} pal. ({o.palette_format})"],["Poids",f"{o.total_weight or 0:.1f} T"]]
    elif claim.claim_type=="crew":
        if claim.crew_member: dd.append(["Personne",f"{claim.crew_member.full_name} ({claim.crew_member.role_label})"])
    t = Table(dd, colWidths=[140,330])
    t.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#095561')),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(t); story.append(Spacer(1,10))
    story.append(Paragraph("Description de l'incident", hs))
    story.append(Paragraph(claim.description.replace('\n','<br/>'), bs))
    story.append(Spacer(1,10))
    if claim.documents:
        story.append(Paragraph("Documents de preuve", hs))
        for i,d in enumerate(claim.documents,1):
            story.append(Paragraph(f"{i}. {d.doc_type_label} — {d.title}" + (f" ({d.filename})" if d.filename else ""), bs))
    story.append(Spacer(1,10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray))
    story.append(Spacer(1,6))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} par {user.full_name}", xs))
    story.append(Paragraph("TOWT SAS — Transport à la Voile — www.towt.eu", xs))
    doc.build(story)

    db.add(ClaimTimeline(claim_id=claim_id, action_type="declaration", title="Déclaration PDF générée", filename=f"declaration_{claim.reference}.pdf", file_path=pdf_path, actor=user.full_name, action_date=datetime.now()))
    await db.flush()
    from app.utils.safe_files import safe_file_response
    return safe_file_response(pdf_path, filename=f"declaration_{claim.reference}.pdf", media_type="application/pdf")
