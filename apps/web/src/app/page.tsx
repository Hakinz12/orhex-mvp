import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  Blocks,
  BrainCircuit,
  ChevronRight,
  Command,
  CircleHelp,
  Database,
  LockKeyhole,
  MessageSquareText,
  Network,
  Orbit,
  Radio,
  ShieldCheck,
  Sparkles,
  Waves,
} from "lucide-react";
import { OrbitMark } from "@/components/orbit-mark";
import { IntegrationConsole } from "@/components/integration-console";

const navigation = [
  { label: "Overview", href: "#overview", icon: Orbit, active: true },
  { label: "AI Workspace", href: "#workspace", icon: MessageSquareText },
  { label: "Walrus Memory", href: "#memory", icon: Database },
  { label: "Sui Intelligence", href: "#network", icon: Network },
];

function StatusPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="status-pill">
      <span className="status-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export default function Home() {
  return (
    <div className="app-frame" id="overview">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="ORHEX home">
          <span className="brand-mark"><OrbitMark /></span>
          <span className="brand-copy">
            <strong>ORHEX</strong>
            <small>Your World. Understood.</small>
          </span>
        </a>

        <div className="sidebar-rule" />
        <p className="nav-caption">Workspace</p>
        <nav className="primary-nav" aria-label="Workspace navigation">
          {navigation.map(({ label, href, icon: Icon, active }) => (
            <a
              className={`nav-link${active ? " active" : ""}`}
              href={href}
              key={href}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={17} strokeWidth={1.7} />
              <span>{label}</span>
              {active && <span className="nav-indicator" />}
            </a>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="privacy-card">
            <div className="privacy-heading">
              <span className="privacy-icon"><ShieldCheck size={17} /></span>
              <span>Private by design</span>
            </div>
            <p>Provider access stays on the server. Your context remains yours.</p>
            <span className="privacy-label"><LockKeyhole size={11} /> Protected workspace</span>
          </div>
          <div className="sidebar-foot">
            <span className="tiny-orbit"><OrbitMark /></span>
            <span>ORHEX OS <span className="foot-separator">/</span> 2026</span>
            <CircleHelp size={15} aria-label="Help" />
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <a className="mobile-brand" href="#overview" aria-label="ORHEX home">
            <span className="brand-mark"><OrbitMark /></span>
            <strong>ORHEX</strong>
          </a>
          <div className="breadcrumbs">
            <span>Workspace</span><ChevronRight size={13} /><strong>Overview</strong>
          </div>
          <div className="topbar-right">
            <div className="private-status"><span className="live-dot" />Private workspace</div>
            <button className="profile-button" type="button" aria-label="Workspace profile">
              <OrbitMark />
            </button>
          </div>
        </header>

        <div className="dashboard">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> PERSONAL INTELLIGENCE <span className="eyebrow-divider">/</span> TOTAL RECALL 2026</div>
              <h1>Your world, <span>in context.</span></h1>
              <p className="welcome-copy">A personal intelligence system that remembers what matters, connects the dots, and helps you move forward.</p>
            </div>
            <div className="workspace-state"><span className="state-glyph"><Command size={15} /></span><span><strong>Workspace</strong><small>Foundation ready</small></span><StatusPill>SETUP</StatusPill></div>
          </section>

          <section className="hero-card" aria-labelledby="hero-title">
            <div className="hero-copy">
              <span className="hero-kicker"><Sparkles size={13} /> YOUR PERSONAL INTELLIGENCE LAYER</span>
              <h2 id="hero-title">A little more <em>understood.</em></h2>
              <p>Bring your conversations, memories, and on-chain signals into one thoughtful space. Your information stays under your control.</p>
              <div className="hero-actions">
                <a className="button-primary" href="#workspace">Explore workspace <ArrowRight size={15} /></a>
                <a className="button-subtle" href="#integrations">View system map <ArrowUpRight size={14} /></a>
              </div>
              <div className="hero-assurances">
                <span><ShieldCheck size={14} /> Private by design</span>
                <span><Waves size={14} /> Memory with continuity</span>
                <span><Radio size={14} /> Read-only chain insight</span>
              </div>
            </div>
            <div className="orbit-art" aria-hidden="true">
              <div className="orbit-halo" />
              <div className="orbit-ring ring-outer"><i className="orbit-node node-top" /><i className="orbit-node node-bottom" /></div>
              <div className="orbit-ring ring-middle"><i className="orbit-node node-right" /></div>
              <div className="orbit-ring ring-inner"><i className="orbit-center"><OrbitMark /></i></div>
              <span className="orbit-label label-memory"><span /> MEMORY</span>
              <span className="orbit-label label-ai"><span /> AI</span>
              <span className="orbit-label label-chain"><span /> SUI</span>
            </div>
            <div className="hero-grid" aria-hidden="true" />
          </section>

          <section className="section-heading" id="integrations">
            <div>
              <div className="eyebrow">YOUR SYSTEM</div>
              <h2>Built to work together</h2>
              <p>Three connected capabilities. Clear boundaries. Your context at the center.</p>
            </div>
            <span className="integration-note"><span className="status-dot" /> Connections not configured</span>
          </section>

          <section className="feature-grid" aria-label="ORHEX capabilities">
            <article className="feature-card memory-card" id="memory">
              <div className="card-topline">
                <span className="feature-icon memory-icon"><Database size={19} strokeWidth={1.7} /></span>
                <span className="feature-state">NOT CONNECTED</span>
              </div>
              <div className="feature-title-row"><h3>Walrus Memory</h3><span className="provider-tag">PERSISTENT</span></div>
              <p className="feature-description">Your important context, stored with confirmation and ready to be recalled when it matters.</p>
              <div className="card-bottom">
                <span className="empty-status"><span className="status-dot" />No memories saved</span>
                <a className="card-link" href="#setup-memory" aria-label="See Walrus Memory setup status"><ArrowUpRight size={16} /></a>
              </div>
            </article>

            <article className="feature-card workspace-card" id="workspace">
              <div className="card-topline">
                <span className="feature-icon ai-icon"><BrainCircuit size={20} strokeWidth={1.65} /></span>
                <span className="feature-state">COMING NEXT</span>
              </div>
              <div className="feature-title-row"><h3>AI Workspace</h3><span className="provider-tag violet-tag">CONTEXTUAL</span></div>
              <p className="feature-description">A thoughtful assistant that can carry useful context across conversations, with you in control.</p>
              <div className="card-bottom">
                <span className="empty-status"><MessageSquareText size={13} />No conversations yet</span>
                <a className="card-link violet-link" href="#setup-ai" aria-label="See AI Workspace setup status"><ArrowUpRight size={16} /></a>
              </div>
            </article>

            <article className="feature-card network-card" id="network">
              <div className="card-topline">
                <span className="feature-icon chain-icon"><Blocks size={19} strokeWidth={1.7} /></span>
                <span className="feature-state">NOT CONNECTED</span>
              </div>
              <div className="feature-title-row"><h3>Sui Intelligence</h3><span className="provider-tag">READ-ONLY</span></div>
              <p className="feature-description">Understand public Sui wallet activity and balances through live, attributed network data.</p>
              <div className="card-bottom">
                <span className="empty-status"><Network size={13} />Tatum provider not configured</span>
                <a className="card-link blue-link" href="#setup-network" aria-label="See Sui Intelligence setup status"><ArrowUpRight size={16} /></a>
              </div>
            </article>
          </section>

          <IntegrationConsole />

          <section className="lower-grid" aria-label="Workspace status">
            <article className="activity-card">
              <div className="panel-heading">
                <div><div className="eyebrow">AT A GLANCE</div><h2>A calm place to begin</h2></div>
                <span className="panel-icon"><AudioLines size={17} /></span>
              </div>
              <div className="empty-activity">
                <span className="empty-orbit"><OrbitMark /></span>
                <div><strong>Your workspace is ready to take shape</strong><p>Connect an integration to bring real context into view. No sample activity is shown here.</p></div>
                <ArrowDownRight className="empty-arrow" size={18} />
              </div>
              <div className="activity-footer"><span>LIVE DATA ONLY</span><span className="footer-line" /><span>Nothing is simulated</span></div>
            </article>

            <article className="setup-card" id="setup-memory">
              <div className="panel-heading">
                <div><div className="eyebrow">SYSTEM STATUS</div><h2>Integrations</h2></div>
                <span className="status-ring"><span /></span>
              </div>
              <div className="setup-list">
                <div className="setup-row">
                  <span className="setup-symbol walrus-symbol"><Database size={15} /></span>
                  <span className="setup-name"><strong>Walrus Memory</strong><small id="setup-ai">Persistent context</small></span>
                  <span className="setup-pending">Not configured</span>
                </div>
                <div className="setup-row" id="setup-network">
                  <span className="setup-symbol tatum-symbol"><Network size={15} /></span>
                  <span className="setup-name"><strong>Tatum · Sui</strong><small>Read-only blockchain data</small></span>
                  <span className="setup-pending">Not configured</span>
                </div>
                <div className="setup-row">
                  <span className="setup-symbol ai-symbol"><Sparkles size={15} /></span>
                  <span className="setup-name"><strong>AI provider</strong><small>Assistant responses</small></span>
                  <span className="setup-pending">Not configured</span>
                </div>
              </div>
              <div className="setup-footer"><LockKeyhole size={13} /><span>Credentials will be kept server-side</span><ArrowRight size={14} /></div>
            </article>
          </section>

          <footer className="page-footer">
            <span><OrbitMark /> <strong>ORHEX</strong> <span className="footer-dot">·</span> Your World. Understood.</span>
            <span>BUILT FOR CONTEXT. DESIGNED FOR TRUST.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
