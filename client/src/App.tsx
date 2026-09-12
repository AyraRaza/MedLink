// MedLink quiet-luxury SaaS system: warm canvas, black rail, soft pastel signals, calm operational motion.
import { useEffect, useState } from "react";
import {
  Activity, AlertCircle, ArrowLeft, Bell, Building2, ChevronRight, CircleHelp,
  ClipboardList, Database, Droplets, LayoutDashboard, LogOut, Menu, Package,
  Pencil, Plus, Search, Settings, ShieldCheck, SlidersHorizontal, Sparkles,
  Stethoscope, Syringe, X, Zap
} from "lucide-react";
import { toast } from "sonner";
import { apiClient, getApiErrorMessage } from "@/lib/api";
import { clearAccessToken, getAccessToken, getCurrentUser, login, registerUser, type User } from "@/lib/auth";

const logo = "/assets/medlink-logo.svg";
const networkArt = "/assets/medlink-network.svg";
const opsArt = "/assets/medlink-operations.svg";
const authArt = "/assets/medlink-auth.svg";

type View = "dashboard" | "inventory" | "resource" | "add" | "edit" | "organization" | "settings" | "login" | "onboarding";
type OrganizationData = { id: number; name: string; registration_number: string; organization_type: string; email: string | null; phone: string | null; address: string | null; city: string | null; state: string | null; pincode: string | null; verification_status: "PENDING" | "VERIFIED" | "REJECTED"; is_active: boolean; created_at: string; updated_at: string };
type ResourceCategory = "EQUIPMENT" | "MEDICINE" | "BLOOD" | "MEDICAL_SUPPLY" | "OTHER";
type AvailabilityStatus = "AVAILABLE" | "LOW_STOCK" | "OUT_OF_STOCK" | "UNAVAILABLE";
type ResourceCondition = "NEW" | "GOOD" | "USED" | "DAMAGED";
type ResourceData = { id: number; organization_id: number; name: string; category: ResourceCategory; description: string | null; quantity: number; unit: string; availability_status: AvailabilityStatus; condition: ResourceCondition; expiry_date: string | null; is_active: boolean; created_at: string; updated_at: string };
type ResourceDraft = { name: string; category: ResourceCategory | ""; description: string; quantity: string; unit: string; availability_status: AvailabilityStatus | ""; condition: ResourceCondition | ""; expiry_date: string };

const organizationTypeValues: Record<string, OrganizationData["organization_type"]> = {
  Hospital: "HOSPITAL",
  Clinic: "CLINIC",
  "Diagnostic Center": "DIAGNOSTIC_CENTER",
  "Blood Bank": "BLOOD_BANK",
  Other: "OTHER",
};

const organizationTypeLabels: Record<string, string> = {
  HOSPITAL: "Hospital",
  CLINIC: "Clinic",
  DIAGNOSTIC_CENTER: "Diagnostic Center",
  BLOOD_BANK: "Blood Bank",
  OTHER: "Other",
};

function organizationTypeLabel(value: string) { return organizationTypeLabels[value] || value; }
function verificationLabel(value: OrganizationData["verification_status"]) { return value[0] + value.slice(1).toLowerCase(); }

type MockResource = { name: string; category: string; quantity: string; unit: string; status: string; condition: string; expiry?: string; icon: any };
const dashboardResources: MockResource[] = [
  { name: "Infusion Pump IP-400", category: "Equipment", quantity: "18", unit: "units", status: "AVAILABLE", condition: "Excellent", icon: Activity },
  { name: "Nitrile Examination Gloves", category: "Medical Supply", quantity: "2,840", unit: "pairs", status: "LOW STOCK", condition: "New", expiry: "Nov 2027", icon: Package },
  { name: "O-Negative Blood", category: "Blood", quantity: "12", unit: "units", status: "AVAILABLE", condition: "Cold chain", expiry: "Sep 14, 2026", icon: Droplets },
  { name: "Portable Oxygen Cylinder", category: "Equipment", quantity: "0", unit: "units", status: "OUT OF STOCK", condition: "—", icon: Stethoscope },
  { name: "Amoxicillin 500mg", category: "Medicine", quantity: "160", unit: "packs", status: "AVAILABLE", condition: "Sealed", expiry: "Mar 2028", icon: Syringe },
];
const resources = dashboardResources;

const categoryLabels: Record<ResourceCategory, string> = { EQUIPMENT: "Equipment", MEDICINE: "Medicine", BLOOD: "Blood", MEDICAL_SUPPLY: "Medical Supply", OTHER: "Other" };
const availabilityLabels: Record<AvailabilityStatus, string> = { AVAILABLE: "Available", LOW_STOCK: "Low stock", OUT_OF_STOCK: "Out of stock", UNAVAILABLE: "Unavailable" };
const conditionLabels: Record<ResourceCondition, string> = { NEW: "New", GOOD: "Good", USED: "Used", DAMAGED: "Damaged" };
const categoryOptions = Object.entries(categoryLabels) as [ResourceCategory, string][];
const availabilityOptions = Object.entries(availabilityLabels) as [AvailabilityStatus, string][];
const conditionOptions = Object.entries(conditionLabels) as [ResourceCondition, string][];

function resourceIcon(category: ResourceCategory) { return category === "BLOOD" ? Droplets : category === "MEDICINE" ? Syringe : category === "MEDICAL_SUPPLY" ? Package : category === "OTHER" ? Database : category === "EQUIPMENT" ? Activity : Stethoscope; }
function resourceStatus(status: AvailabilityStatus) { return status.replace("_", " "); }
function formatExpiry(value: string | null) { return value ? new Date(value).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "Not applicable"; }
function dateInputValue(value: string | null) { return value ? value.slice(0, 10) : ""; }
function resourceToDraft(resource?: ResourceData): ResourceDraft { return { name: resource?.name || "", category: resource?.category || "", description: resource?.description || "", quantity: resource ? String(resource.quantity) : "", unit: resource?.unit || "", availability_status: resource?.availability_status || "", condition: resource?.condition || "", expiry_date: dateInputValue(resource?.expiry_date || null) }; }

const nav = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "inventory", label: "Inventory", icon: ClipboardList },
  { id: "resource", label: "Resources", icon: Database },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

function StatusPill({ status, label = status }: { status: string; label?: string }) {
  const styles: Record<string, string> = {
    AVAILABLE: "bg-[#e6f3eb] text-[#397154]",
    "LOW STOCK": "bg-[#fff0d9] text-[#956a2b]",
    "OUT OF STOCK": "bg-[#f3e8e9] text-[#98666b]",
    UNAVAILABLE: "bg-[#ececed] text-[#6d6d71]",
    VERIFIED: "bg-[#e6f3eb] text-[#397154]",
    PENDING: "bg-[#fff0d9] text-[#956a2b]",
  };
  return <span className={`status-pill ${styles[status] || "bg-[#ececed] text-[#666]"}`}><span className="status-dot" />{label}</span>;
}

function Sidebar({ view, setView, mobileOpen, setMobileOpen, onLogout }: { view: View; setView: (v: View) => void; mobileOpen: boolean; setMobileOpen: (v: boolean) => void; onLogout: () => void }) {
  return <>
    <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
      <div className="brand" onClick={() => { setView("dashboard"); setMobileOpen(false); }}>
        <div className="brand-mark"><img src={logo} alt="" /></div><span>MEDLINK</span>
      </div>
      <div className="workspace"><div className="workspace-avatar">AH</div><div><strong>Ardent Health</strong><small>Healthcare Network</small></div><ChevronRight size={15} /></div>
      <div className="nav-group"><small className="nav-caption">WORKSPACE</small>{nav.map(item => { const Icon = item.icon; return <button key={item.id} className={`nav-item ${view === item.id || (view === "add" && item.id === "inventory") ? "active" : ""}`} onClick={() => { setView(item.id); setMobileOpen(false); }}><Icon size={18} /><span>{item.label}</span>{item.id === "inventory" && <span className="nav-count">5</span>}</button> })}</div>
      <div className="rail-note"><Sparkles size={16} /><p><strong>Keep critical resources in view.</strong><br />Your inventory is in good standing.</p></div>
      <div className="sidebar-bottom"><button className="nav-item" onClick={() => toast.info("Help center is coming soon.")}><CircleHelp size={18} /><span>Help center</span></button><button className="nav-item" onClick={onLogout}><LogOut size={18} /><span>Log out</span></button><div className="rail-user"><div className="avatar">JD</div><div><strong>Jordan Davis</strong><small>Inventory admin</small></div><Settings size={15} /></div></div>
    </aside>
    {mobileOpen && <div className="mobile-scrim" onClick={() => setMobileOpen(false)} />}
  </>;
}

function Topbar({ title, setView, setMobileOpen, searchQuery = "", setSearchQuery }: { title: string; setView: (v: View) => void; setMobileOpen: (v: boolean) => void; searchQuery?: string; setSearchQuery?: (value: string) => void }) {
  return <header className="topbar"><div className="mobile-menu" onClick={() => window.dispatchEvent(new Event("medlink:open-nav"))}><Menu size={21} /></div><div><p className="eyebrow">ARDENT HEALTH NETWORK / 08:42 AM</p><h1>{title}</h1></div><div className="top-actions"><div className="searchbox"><Search size={17} /><input placeholder="Search resources" value={searchQuery} onChange={(event) => setSearchQuery?.(event.target.value)} /></div><button className="icon-button" onClick={() => toast.info("You are all caught up.")}><Bell size={18} /><span className="notification-dot" /></button><button className="top-profile" onClick={() => setView("settings")}><div className="avatar">JD</div><span>Jordan Davis</span><ChevronRight size={15} /></button></div></header>;
}

function Metric({ label, value, note, tone, icon: Icon }: any) { return <div className={`metric-card ${tone}`}><div className="metric-top"><span>{label}</span><div className="metric-icon"><Icon size={17} /></div></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>; }

function Dashboard({ setView }: { setView: (v: View) => void }) {
  return <div className="page"><Topbar title="Good morning, Jordan" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><div className="intro-row"><div><p className="section-kicker">TUESDAY, AUGUST 30, 2026</p><h2>Here’s your resource pulse.</h2><p className="muted">A clear view of what your teams have, need, and can act on next.</p></div><button className="button primary" onClick={() => setView("add")}><Plus size={17} /> Add resource</button></div><div className="metrics-grid"><Metric label="Total resources" value="128" note="Across 5 categories" tone="lilac" icon={Database} /><Metric label="Available" value="96" note="75% of inventory" tone="mint" icon={ShieldCheck} /><Metric label="Low stock" value="08" note="Needs attention" tone="peach" icon={AlertCircle} /><Metric label="Out of stock" value="02" note="Review this week" tone="blue" icon={Zap} /></div><div className="main-grid"><section className="card recent-card"><div className="card-heading"><div><p className="section-kicker">LIVE INVENTORY</p><h3>Recent resources</h3></div><button className="text-button" onClick={() => setView("inventory")}>View inventory <ChevronRight size={15} /></button></div><div className="resource-list">{resources.slice(0, 4).map((r, i) => <ResourceRow key={r.name} resource={r} onClick={() => setView("resource")} delay={i} />)}</div></section><section className="overview-card"><div className="overview-copy"><div><p className="section-kicker">ORGANIZATION OVERVIEW</p><h3>Connected, current,<br /><em>in control.</em></h3></div><span className="overview-badge"><Activity size={13} /> Syncing</span></div><div className="overview-art"><img src={networkArt} alt="Abstract connected healthcare network" /></div><div className="overview-foot"><div><strong>5</strong><span>active categories</span></div><div><strong>98.4%</strong><span>data completeness</span></div><button onClick={() => setView("organization")}>Organization profile <ChevronRight size={15} /></button></div></section></div><div className="bottom-grid"><section className="card status-card"><div className="card-heading"><div><p className="section-kicker">ORGANIZATION STATUS</p><h3>Verified organization</h3></div><StatusPill status="VERIFIED" /></div><p className="muted">Ardent Health Network is verified for biomedical resource management.</p><div className="progress-line"><span style={{ width: "100%" }} /></div><div className="status-meta"><span>Verification complete</span><span>100%</span></div></section><section className="card quick-card"><img src={opsArt} alt="Medical inventory supplies" /><div><p className="section-kicker">QUICK ACTION</p><h3>Keep your catalog current.</h3><button className="text-button" onClick={() => setView("add")}>Add a resource <ChevronRight size={15} /></button></div></section></div></main></div>;
}

function ResourceRow({ resource: r, onClick, delay = 0 }: { resource: MockResource | ResourceData; onClick: () => void; delay?: number }) { const isBackendResource = "id" in r; const Icon = isBackendResource ? resourceIcon(r.category) : r.icon; const category = isBackendResource ? categoryLabels[r.category] : r.category; const quantity = isBackendResource ? String(r.quantity) : r.quantity; const status = isBackendResource ? resourceStatus(r.availability_status) : r.status; return <button className="resource-row" style={{ animationDelay: `${delay * 40}ms` }} onClick={onClick}><div className="resource-icon"><Icon size={17} /></div><div className="resource-name"><strong>{r.name}</strong><span>{category}</span></div><div className="resource-qty"><strong>{quantity}</strong><span>{r.unit}</span></div><StatusPill status={status} label={isBackendResource ? availabilityLabels[r.availability_status] : status} /><ChevronRight size={16} className="row-arrow" /></button>; }

function Inventory({ setView }: { setView: (v: View) => void }) { const [filter, setFilter] = useState("All resources"); return <div className="page"><Topbar title="Biomedical inventory" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><div className="intro-row"><div><p className="section-kicker">RESOURCE CATALOG / 128 ITEMS</p><h2>Everything in one view.</h2><p className="muted">Manage availability, condition, and expiry across your organization.</p></div><button className="button primary" onClick={() => setView("add")}><Plus size={17} /> Add resource</button></div><div className="inventory-toolbar"><div className="filter-chips">{["All resources", "Equipment", "Medicine", "Blood", "Medical Supply"].map(x => <button key={x} className={filter === x ? "selected" : ""} onClick={() => setFilter(x)}>{x}</button>)}</div><button className="filter-button" onClick={() => toast.info("More filters are coming soon.")}><SlidersHorizontal size={16} /> Filters</button></div><section className="card inventory-card"><div className="inventory-head"><span>Resource</span><span>Quantity</span><span>Status</span><span></span></div>{resources.filter(r => filter === "All resources" || r.category === filter).map((r, i) => <ResourceRow key={r.name} resource={r} onClick={() => setView("resource")} delay={i} />)}</section></main></div>; }

function ResourceDetail({ setView }: { setView: (v: View) => void }) { const r = resources[0]; return <div className="page"><Topbar title="Resource details" setView={setView} setMobileOpen={() => {}} /><main className="page-content detail-page"><button className="back-button" onClick={() => setView("inventory")}><ArrowLeft size={16} /> Back to inventory</button><div className="detail-heading"><div><div className="detail-icon"><Activity size={22} /></div><p className="section-kicker">EQUIPMENT / RESOURCE #ML-0041</p><h2>{r.name}</h2><p className="muted">Last updated today at 08:35 AM by Jordan Davis</p></div><div className="detail-actions"><StatusPill status="AVAILABLE" /><button className="button secondary" onClick={() => toast.success("Edit mode is ready in the full app.")}><Pencil size={16} /> Edit resource</button></div></div><div className="detail-stats"><div className="card detail-stat"><span>Quantity</span><strong>18</strong><small>units available</small></div><div className="card detail-stat"><span>Condition</span><strong>Excellent</strong><small>Last inspected Aug 12</small></div><div className="card detail-stat"><span>Active status</span><strong>Active</strong><small>Visible to organization</small></div><div className="card detail-stat"><span>Organization</span><strong>Ardent Health</strong><small>Healthcare Network</small></div></div><div className="detail-columns"><section className="card detail-description"><p className="section-kicker">DESCRIPTION</p><h3>Reliable infusion support for every ward.</h3><p className="muted">IP-400 programmable infusion pumps designed for controlled medication delivery. Each unit is maintained under Ardent Health Network’s biomedical equipment program.</p></section><section className="card detail-meta"><p className="section-kicker">RESOURCE METADATA</p><div><span>Created</span><strong>May 18, 2026</strong></div><div><span>Updated</span><strong>Aug 30, 2026</strong></div><div><span>Expiry</span><strong>Not applicable</strong></div></section></div></main></div>; }

function AddResource({ setView }: { setView: (v: View) => void }) { return <div className="page"><Topbar title="Add resource" setView={setView} setMobileOpen={() => {}} /><main className="page-content form-page"><button className="back-button" onClick={() => setView("inventory")}><ArrowLeft size={16} /> Back to inventory</button><div className="form-intro"><p className="section-kicker">NEW RESOURCE</p><h2>Add a resource to your catalog.</h2><p className="muted">Keep your team’s shared inventory accurate and ready to act on.</p></div><section className="card form-card"><div className="form-grid"><label>Resource name<input placeholder="e.g. Portable oxygen cylinder" /></label><label>Category<select defaultValue=""><option value="" disabled>Select category</option><option>Equipment</option><option>Medicine</option><option>Blood</option><option>Medical Supply</option></select></label><label className="wide">Description<textarea placeholder="Add a short description of this resource..." /></label><label>Quantity<input placeholder="0" type="number" /></label><label>Unit<select defaultValue=""><option value="" disabled>Select unit</option><option>Units</option><option>Packs</option><option>Pairs</option><option>Liters</option></select></label><label>Availability status<select defaultValue=""><option value="" disabled>Select status</option><option>AVAILABLE</option><option>LOW STOCK</option><option>UNAVAILABLE</option></select></label><label>Condition<select defaultValue=""><option value="" disabled>Select condition</option><option>New</option><option>Excellent</option><option>Good</option><option>Needs review</option></select></label><label>Expiry date<input type="date" /></label></div><div className="form-footer"><span className="muted"><ShieldCheck size={15} /> Changes are visible to verified members.</span><div><button className="button secondary" onClick={() => setView("inventory")}>Cancel</button><button className="button primary" onClick={() => { toast.success("Resource added to your catalog."); setView("inventory"); }}>Add resource <Plus size={16} /></button></div></div></section></main></div>; }

function apiStatus(error: unknown) { return (error as { response?: { status?: number } }).response?.status; }

function LiveInventory({ resources, loading, error, searchQuery, setSearchQuery, setView, setSelectedResourceId }: { resources: ResourceData[]; loading: boolean; error: string | null; searchQuery: string; setSearchQuery: (value: string) => void; setView: (v: View) => void; setSelectedResourceId: (id: number) => void }) {
  const [filter, setFilter] = useState<ResourceCategory | "ALL">("ALL");
  const filteredResources = resources.filter((resource) => (filter === "ALL" || resource.category === filter) && `${resource.name} ${resource.description || ""}`.toLowerCase().includes(searchQuery.toLowerCase()));
  return <div className="page"><Topbar title="Biomedical inventory" setView={setView} setMobileOpen={() => {}} searchQuery={searchQuery} setSearchQuery={setSearchQuery} /><main className="page-content"><div className="intro-row"><div><p className="section-kicker">RESOURCE CATALOG / {resources.length} ITEMS</p><h2>Everything in one view.</h2><p className="muted">Manage availability, condition, and expiry across your organization.</p></div><button className="button primary" onClick={() => setView("add")}><Plus size={17} /> Add resource</button></div><div className="inventory-toolbar"><div className="filter-chips"><button className={filter === "ALL" ? "selected" : ""} onClick={() => setFilter("ALL")}>All resources</button>{categoryOptions.map(([value, label]) => <button key={value} className={filter === value ? "selected" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div><button className="filter-button" onClick={() => toast.info("Use the search field or category filters to narrow resources.")}><SlidersHorizontal size={16} /> Filters</button></div>{loading ? <section className="card inventory-card"><p className="muted">Loading inventory...</p></section> : error ? <section className="card inventory-card"><p className="muted">{error}</p></section> : <section className="card inventory-card"><div className="inventory-head"><span>Resource</span><span>Quantity</span><span>Status</span><span></span></div>{filteredResources.length === 0 ? <p className="muted">No resources match your filters.</p> : filteredResources.map((resource, i) => <ResourceRow key={resource.id} resource={resource} onClick={() => { setSelectedResourceId(resource.id); setView("resource"); }} delay={i} />)}</section>}</main></div>;
}

function ResourceForm({ resource, setView, onUnauthorized, onSaved }: { resource?: ResourceData; setView: (v: View) => void; onUnauthorized: () => void; onSaved: (resource: ResourceData) => Promise<void> }) {
  const [draft, setDraft] = useState<ResourceDraft>(() => resourceToDraft(resource));
  const [submitting, setSubmitting] = useState(false);
  const update = (field: keyof ResourceDraft, value: string) => setDraft((current) => ({ ...current, [field]: value }));
  const submit = async () => {
    if (!draft.name.trim() || !draft.category || !draft.quantity.trim() || !draft.unit.trim()) { toast.error("Complete the name, category, quantity, and unit."); return; }
    const quantity = Number(draft.quantity);
    if (!Number.isInteger(quantity) || quantity < 0) { toast.error("Quantity must be a whole number of zero or more."); return; }
    setSubmitting(true);
    const payload = { name: draft.name.trim(), category: draft.category, description: draft.description.trim() || null, quantity, unit: draft.unit.trim(), availability_status: draft.availability_status || "AVAILABLE", condition: draft.condition || "NEW", expiry_date: draft.expiry_date ? `${draft.expiry_date}T00:00:00Z` : null };
    try { const response = resource ? await apiClient.patch<ResourceData>(`/resources/${resource.id}`, payload) : await apiClient.post<ResourceData>("/resources", payload); await onSaved(response.data); toast.success(resource ? "Resource updated." : "Resource added to your catalog."); } catch (error) { if (apiStatus(error) === 401) onUnauthorized(); else toast.error(getApiErrorMessage(error, resource ? "Unable to update the resource." : "Unable to add the resource.")); } finally { setSubmitting(false); }
  };
  return <div className="page"><Topbar title={resource ? "Edit resource" : "Add resource"} setView={setView} setMobileOpen={() => {}} /><main className="page-content form-page"><button className="back-button" onClick={() => setView(resource ? "resource" : "inventory")}><ArrowLeft size={16} /> Back to {resource ? "resource" : "inventory"}</button><div className="form-intro"><p className="section-kicker">{resource ? "EDIT RESOURCE" : "NEW RESOURCE"}</p><h2>{resource ? "Keep this resource current." : "Add a resource to your catalog."}</h2><p className="muted">Keep your team’s shared inventory accurate and ready to act on.</p></div><section className="card form-card"><div className="form-grid"><label>Resource name<input value={draft.name} onChange={(event) => update("name", event.target.value)} placeholder="e.g. Portable oxygen cylinder" /></label><label>Category<select value={draft.category} onChange={(event) => update("category", event.target.value)}><option value="" disabled>Select category</option>{categoryOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="wide">Description<textarea value={draft.description} onChange={(event) => update("description", event.target.value)} placeholder="Add a short description of this resource..." /></label><label>Quantity<input value={draft.quantity} onChange={(event) => update("quantity", event.target.value)} placeholder="0" type="number" min="0" step="1" /></label><label>Unit<input value={draft.unit} onChange={(event) => update("unit", event.target.value)} placeholder="e.g. units" /></label><label>Availability status<select value={draft.availability_status} onChange={(event) => update("availability_status", event.target.value)}><option value="">Available</option>{availabilityOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Condition<select value={draft.condition} onChange={(event) => update("condition", event.target.value)}><option value="">New</option>{conditionOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Expiry date<input value={draft.expiry_date} onChange={(event) => update("expiry_date", event.target.value)} type="date" /></label></div><div className="form-footer"><span className="muted"><ShieldCheck size={15} /> Changes are visible to verified members.</span><div><button className="button secondary" disabled={submitting} onClick={() => setView(resource ? "resource" : "inventory")}>Cancel</button><button className="button primary" disabled={submitting} aria-busy={submitting} onClick={submit}>{submitting ? "Saving..." : resource ? "Save changes" : "Add resource"} <Plus size={16} /></button></div></div></section></main></div>;
}

function LiveResourceDetail({ resource, loading, error, setView, setEdit, onDelete, deleting }: { resource: ResourceData | null; loading: boolean; error: string | null; setView: (v: View) => void; setEdit: () => void; onDelete: () => void; deleting: boolean }) {
  if (loading) return <div className="page"><Topbar title="Resource details" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><p className="muted">Loading resource...</p></main></div>;
  if (error || !resource) return <div className="page"><Topbar title="Resource details" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><button className="back-button" onClick={() => setView("inventory")}><ArrowLeft size={16} /> Back to inventory</button><section className="card"><p className="muted">{error || "Resource not found."}</p></section></main></div>;
  const Icon = resourceIcon(resource.category);
  return <div className="page"><Topbar title="Resource details" setView={setView} setMobileOpen={() => {}} /><main className="page-content detail-page"><button className="back-button" onClick={() => setView("inventory")}><ArrowLeft size={16} /> Back to inventory</button><div className="detail-heading"><div><div className="detail-icon"><Icon size={22} /></div><p className="section-kicker">{categoryLabels[resource.category]} / RESOURCE #{resource.id}</p><h2>{resource.name}</h2><p className="muted">Updated {new Date(resource.updated_at).toLocaleString()}</p></div><div className="detail-actions"><StatusPill status={resourceStatus(resource.availability_status)} label={availabilityLabels[resource.availability_status]} /><button className="button secondary" onClick={setEdit}><Pencil size={16} /> Edit resource</button><button className="button secondary" disabled={deleting} onClick={onDelete}>{deleting ? "Deleting..." : "Delete"} <X size={16} /></button></div></div><div className="detail-stats"><div className="card detail-stat"><span>Quantity</span><strong>{resource.quantity}</strong><small>{resource.unit} available</small></div><div className="card detail-stat"><span>Condition</span><strong>{conditionLabels[resource.condition]}</strong><small>Current condition</small></div><div className="card detail-stat"><span>Active status</span><strong>{resource.is_active ? "Active" : "Inactive"}</strong><small>{resource.is_active ? "Visible to organization" : "Soft deleted"}</small></div><div className="card detail-stat"><span>Expiry</span><strong>{formatExpiry(resource.expiry_date)}</strong><small>{resource.expiry_date ? "Recorded expiry date" : "No expiry recorded"}</small></div></div><div className="detail-columns"><section className="card detail-description"><p className="section-kicker">DESCRIPTION</p><h3>{resource.description || "No description provided."}</h3><p className="muted">This resource is managed within your organization’s biomedical inventory.</p></section><section className="card detail-meta"><p className="section-kicker">RESOURCE METADATA</p><div><span>Created</span><strong>{new Date(resource.created_at).toLocaleDateString()}</strong></div><div><span>Updated</span><strong>{new Date(resource.updated_at).toLocaleDateString()}</strong></div><div><span>Category</span><strong>{categoryLabels[resource.category]}</strong></div></section></div></main></div>;
}

function Organization({ setView, organization, loading, setOrganization, onUnauthorized }: { setView: (v: View) => void; organization: OrganizationData | null; loading: boolean; setOrganization: (organization: OrganizationData) => void; onUnauthorized: () => void }) {
  const [editing, setEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [draft, setDraft] = useState<Partial<OrganizationData>>({});

  useEffect(() => { if (organization) setDraft(organization); }, [organization]);

  if (loading || !organization) return <div className="page"><Topbar title="Organization" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><p className="muted">Loading organization...</p></main></div>;

  const saveOrganization = async () => {
    setIsSaving(true);
    try {
      const { data } = await apiClient.patch<OrganizationData>(`/organizations/${organization.id}`, {
        name: draft.name,
        registration_number: draft.registration_number,
        organization_type: draft.organization_type,
        email: draft.email || null,
        phone: draft.phone || null,
        address: draft.address || null,
        city: draft.city || null,
        state: draft.state || null,
        pincode: draft.pincode || null,
      });
      const refreshed = await apiClient.get<OrganizationData>("/organizations/me");
      setOrganization(refreshed.data || data);
      setEditing(false);
      toast.success("Organization profile updated.");
    } catch (error) {
      if ((error as { response?: { status?: number } }).response?.status === 401) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "Unable to update the organization."));
    } finally { setIsSaving(false); }
  };

  const setDraftField = (field: keyof OrganizationData, value: string) => setDraft((current) => ({ ...current, [field]: value }));
  const address = [organization.address, organization.city, organization.state, organization.pincode].filter(Boolean).join(", ") || "Not provided";
  return <div className="page"><Topbar title="Organization" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><div className="intro-row"><div><p className="section-kicker">ORGANIZATION PROFILE</p><h2>{organization.name}</h2><p className="muted">The verified identity behind your resource catalog.</p></div><button className="button secondary" disabled={isSaving} onClick={() => setEditing((current) => !current)}><Pencil size={16} /> {editing ? "Cancel" : "Edit profile"}</button></div><section className="org-hero card"><div className="org-symbol"><Building2 size={26} /></div><div><h3>{organization.name}</h3><p className="muted">{organizationTypeLabel(organization.organization_type)} · {[organization.city, organization.state].filter(Boolean).join(", ") || "Location not provided"}</p></div><StatusPill status={organization.verification_status} label={verificationLabel(organization.verification_status)} /></section><div className="org-grid"><section className="card info-card"><p className="section-kicker">ORGANIZATION DETAILS</p>{editing ? <><label className="form-grid"><span>Name<input value={draft.name || ""} onChange={(event) => setDraftField("name", event.target.value)} /></span><span>Registration number<input value={draft.registration_number || ""} onChange={(event) => setDraftField("registration_number", event.target.value)} /></span><span>Email<input value={draft.email || ""} onChange={(event) => setDraftField("email", event.target.value)} /></span><span>Phone<input value={draft.phone || ""} onChange={(event) => setDraftField("phone", event.target.value)} /></span><span>Address<input value={draft.address || ""} onChange={(event) => setDraftField("address", event.target.value)} /></span><span>City<input value={draft.city || ""} onChange={(event) => setDraftField("city", event.target.value)} /></span><span>State<input value={draft.state || ""} onChange={(event) => setDraftField("state", event.target.value)} /></span><span>Pincode<input value={draft.pincode || ""} onChange={(event) => setDraftField("pincode", event.target.value)} /></span></label><button className="button primary" disabled={isSaving} onClick={saveOrganization}>{isSaving ? "Saving..." : "Save changes"}</button></> : [["Registration number", organization.registration_number], ["Organization type", organizationTypeLabel(organization.organization_type)], ["Email", organization.email || "Not provided"], ["Phone", organization.phone || "Not provided"], ["Address", organization.address || "Not provided"], ["City / State", address]].map(([a, b]) => <div className="info-line" key={a}><span>{a}</span><strong>{b}</strong></div>)}</section><section className="card verification-card"><p className="section-kicker">VERIFICATION STATUS</p><div className="verify-ring"><ShieldCheck size={28} /></div><h3>{verificationLabel(organization.verification_status)} organization</h3><p className="muted">Your organization is currently {verificationLabel(organization.verification_status).toLowerCase()}. You can manage biomedical resources for your network.</p><button className="text-button" onClick={() => toast.info("Verification details are available to administrators.")}>View verification details <ChevronRight size={15} /></button></section></div></main></div>;
}

function SettingsPage({ setView }: { setView: (v: View) => void }) { return <div className="page"><Topbar title="Settings" setView={setView} setMobileOpen={() => {}} /><main className="page-content"><div className="form-intro"><p className="section-kicker">ACCOUNT & PREFERENCES</p><h2>Settings</h2><p className="muted">Manage your profile and notification preferences.</p></div><div className="settings-grid"><section className="card settings-card"><p className="section-kicker">PROFILE INFORMATION</p><div className="profile-large"><div className="avatar avatar-lg">JD</div><div><h3>Jordan Davis</h3><p className="muted">Inventory admin</p></div><button className="button secondary small" onClick={() => toast.info("Profile editing is coming soon.")}>Edit</button></div>{[["Full name","Jordan Davis"],["Email","jordan.davis@ardenthealth.org"],["Role","Inventory administrator"]].map(([a,b]) => <div className="info-line" key={a}><span>{a}</span><strong>{b}</strong></div>)}</section><section className="card settings-card"><p className="section-kicker">ACCOUNT SETTINGS</p><div className="setting-row"><div><strong>Email notifications</strong><span>Receive updates about low stock</span></div><div className="toggle on"><span /></div></div><div className="setting-row"><div><strong>Weekly inventory digest</strong><span>A Monday summary for your network</span></div><div className="toggle on"><span /></div></div><div className="setting-row"><div><strong>Security alerts</strong><span>Important access and profile changes</span></div><div className="toggle on"><span /></div></div></section></div></main></div>; }

function Login({ setView, onAuthenticated }: { setView: (v: View) => void; onAuthenticated: () => Promise<void> }) {
  const [email, setEmail] = useState("jordan.davis@ardenthealth.org");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password) {
      toast.error("Enter your email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email, password);
      toast.success("Welcome back.");
      await onAuthenticated();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Unable to sign in. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return <div className="auth-page"><div className="auth-visual"><div className="auth-brand"><div className="brand-mark"><img src={logo} alt="" /></div><span>MEDLINK</span></div><div className="auth-art"><img src={authArt} alt="Connected medical cross illustration" /></div><div className="auth-quote"><p>“Clarity is care in motion.”</p><span>MedLink for verified healthcare organizations.</span></div></div><div className="auth-form"><div className="auth-form-inner"><p className="section-kicker">WELCOME BACK</p><h1>Sign in to MedLink.</h1><p className="muted">Manage what matters across your healthcare network.</p><label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><div className="form-inline"><label className="check"><input type="checkbox" defaultChecked /> Remember me</label><button className="text-button" onClick={() => toast.info("Password reset is coming soon.")}>Forgot password?</button></div><button className="button primary full" disabled={isSubmitting} aria-busy={isSubmitting} onClick={handleLogin}>{isSubmitting ? "Signing in..." : "Sign in"} <ChevronRight size={17} /></button><p className="auth-switch">New to MedLink? <button onClick={() => setView("onboarding")}>Create an account</button></p></div></div></div>;
}

function Onboarding({ setView, setupOnly, onCreated }: { setView: (v: View) => void; setupOnly: boolean; onCreated: (organization: OrganizationData) => void }) {
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [organizationType, setOrganizationType] = useState("");
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitOnboarding = async () => {
    if ((!setupOnly && (!fullName.trim() || !password || !email.trim())) || !organizationName.trim() || !registrationNumber.trim() || !organizationType) {
      toast.error(setupOnly ? "Complete the organization details." : "Complete your account and organization details.");
      return;
    }
    if (!setupOnly && password.length < 8) { toast.error("Password must be at least 8 characters."); return; }

    setIsSubmitting(true);
    try {
      if (!setupOnly) {
        await registerUser({ email, password, full_name: fullName });
        await login(email, password);
      }
      await apiClient.post("/organizations", { name: organizationName, registration_number: registrationNumber, organization_type: organizationTypeValues[organizationType], email: email || null });
      const { data } = await apiClient.get<OrganizationData>("/organizations/me");
      onCreated(data);
      toast.success("Organization created.");
      setView("organization");
    } catch (error) {
      if ((error as { response?: { status?: number } }).response?.status === 401) { clearAccessToken(); setView("login"); }
      else toast.error(getApiErrorMessage(error, "Unable to complete onboarding."));
    } finally { setIsSubmitting(false); }
  };

  return <div className="auth-page"><div className="auth-visual onboarding-visual"><div className="auth-brand"><div className="brand-mark"><img src={logo} alt="" /></div><span>MEDLINK</span></div><div className="onboarding-copy"><p className="section-kicker">STEP 02 / ORGANIZATION</p><h1>Bring your organization into view.</h1><p>Verified healthcare teams use MedLink to keep biomedical resources clear, current, and ready.</p><div className="onboarding-steps"><span className="done">01</span><span className="line" /><span className="current">02</span><span className="line" /><span>03</span></div></div></div><div className="auth-form"><div className="auth-form-inner"><p className="section-kicker">{setupOnly ? "REGISTER ORGANIZATION" : "CREATE YOUR ACCOUNT"}</p><h1>{setupOnly ? "Tell us about your team." : "Create your MedLink workspace."}</h1><p className="muted">We’ll review these details before activating your workspace.</p><div className="form-grid compact">{!setupOnly && <><label className="wide">Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="e.g. Jordan Davis" /></label><label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@organization.org" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label></>}<label className="wide">Organization name<input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} placeholder="e.g. Ardent Health Network" /></label><label>Registration number<input value={registrationNumber} onChange={(event) => setRegistrationNumber(event.target.value)} placeholder="Registration ID" /></label><label>Organization type<select value={organizationType} onChange={(event) => setOrganizationType(event.target.value)}><option value="" disabled>Select type</option>{Object.keys(organizationTypeValues).map((label) => <option key={label}>{label}</option>)}</select></label></div><button className="button primary full" disabled={isSubmitting} onClick={submitOnboarding}>{isSubmitting ? (setupOnly ? "Creating organization..." : "Creating account...") : "Submit for verification"} <ChevronRight size={17} /></button><p className="auth-switch">Already have an account? <button onClick={() => setView("login")}>Sign in</button></p></div></div></div>;
}

export default function App() {
  const [view, setView] = useState<View>("login");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [organization, setOrganization] = useState<OrganizationData | null>(null);
  const [organizationLoading, setOrganizationLoading] = useState(false);
  const [setupOnly, setSetupOnly] = useState(false);
  const [resources, setResources] = useState<ResourceData[]>([]);
  const [selectedResourceId, setSelectedResourceId] = useState<number | null>(null);
  const [resourceDetail, setResourceDetail] = useState<ResourceData | null>(null);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { const openNav = () => setMobileOpen(true); window.addEventListener("medlink:open-nav", openNav); return () => window.removeEventListener("medlink:open-nav", openNav); }, []);
  const loadOrganization = async () => { setOrganizationLoading(true); try { const { data } = await apiClient.get<OrganizationData>("/organizations/me"); setOrganization(data); setSetupOnly(false); return true; } catch (error) { const status = apiStatus(error); if (status === 404) { setSetupOnly(true); return false; } if (status === 401) { clearAccessToken(); setView("login"); } else toast.error(getApiErrorMessage(error, "Unable to load the organization.")); return false; } finally { setOrganizationLoading(false); } };
  const handleLogout = () => { clearAccessToken(); setOrganization(null); setView("login"); setMobileOpen(false); toast.success("You have been signed out."); };
  const loadResources = async () => { setInventoryLoading(true); setResourceError(null); try { const { data } = await apiClient.get<ResourceData[]>("/resources"); setResources(data); } catch (error) { if (apiStatus(error) === 401) handleLogout(); else { const message = getApiErrorMessage(error, "Unable to load inventory."); setResourceError(message); toast.error(message); } } finally { setInventoryLoading(false); } };
  const loadResourceDetail = async (id: number) => { setResourceLoading(true); setResourceError(null); try { const { data } = await apiClient.get<ResourceData>(`/resources/${id}`); setResourceDetail(data); } catch (error) { if (apiStatus(error) === 401) handleLogout(); else { const message = apiStatus(error) === 403 ? "You do not have access to this resource." : apiStatus(error) === 404 ? "This resource was not found." : getApiErrorMessage(error, "Unable to load the resource."); setResourceError(message); toast.error(message); setResourceDetail(null); } } finally { setResourceLoading(false); } };
  useEffect(() => { if (view === "inventory") loadResources(); }, [view]);
  useEffect(() => { if (view === "resource" && selectedResourceId !== null) loadResourceDetail(selectedResourceId); }, [view, selectedResourceId]);
  useEffect(() => { if (!getAccessToken()) return; getCurrentUser().then(() => loadOrganization().then((hasOrganization) => setView(hasOrganization ? "dashboard" : "onboarding"))).catch(() => { clearAccessToken(); setView("login"); }); }, []);
  const handleAuthenticated = async () => { const hasOrganization = await loadOrganization(); setView(hasOrganization ? "dashboard" : "onboarding"); };
  const handleOrganizationCreated = (createdOrganization: OrganizationData) => { setOrganization(createdOrganization); setSetupOnly(false); };
  const handleResourceSaved = async (savedResource: ResourceData) => { setResourceDetail(savedResource); await loadResources(); setSelectedResourceId(savedResource.id); setView(view === "edit" ? "resource" : "inventory"); };
  const handleDelete = async () => { if (!resourceDetail || !window.confirm(`Delete ${resourceDetail.name} from active inventory?`)) return; setDeleting(true); try { await apiClient.delete(`/resources/${resourceDetail.id}`); await loadResources(); setResourceDetail(null); setView("inventory"); toast.success("Resource removed from active inventory."); } catch (error) { if (apiStatus(error) === 401) handleLogout(); else toast.error(getApiErrorMessage(error, "Unable to delete the resource.")); } finally { setDeleting(false); } };
  const content = view === "dashboard" ? <Dashboard setView={setView} /> : view === "inventory" ? <LiveInventory resources={resources} loading={inventoryLoading} error={resourceError} searchQuery={searchQuery} setSearchQuery={setSearchQuery} setView={setView} setSelectedResourceId={setSelectedResourceId} /> : view === "resource" ? <LiveResourceDetail resource={resourceDetail} loading={resourceLoading} error={resourceError} setView={setView} setEdit={() => setView("edit")} onDelete={handleDelete} deleting={deleting} /> : view === "add" ? <ResourceForm setView={setView} onUnauthorized={handleLogout} onSaved={handleResourceSaved} /> : view === "edit" ? <ResourceForm resource={resourceDetail || undefined} setView={setView} onUnauthorized={handleLogout} onSaved={handleResourceSaved} /> : view === "organization" ? <Organization setView={setView} organization={organization} loading={organizationLoading} setOrganization={setOrganization} onUnauthorized={handleLogout} /> : view === "settings" ? <SettingsPage setView={setView} /> : view === "login" ? <Login setView={setView} onAuthenticated={handleAuthenticated} /> : <Onboarding setView={setView} setupOnly={setupOnly} onCreated={handleOrganizationCreated} />;
  return view === "login" || view === "onboarding" ? content : <div className="app-shell"><Sidebar view={view} setView={setView} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} onLogout={handleLogout} />{content}</div>;
}
