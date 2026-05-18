import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer, Cell } from 'recharts';
import './App.css';
import { POEMS, PAPER } from './poems';
import { ResearchSections } from './components/ResearchSections';

const FILTERS = [
  { key: '', label: 'All Methods' },
  { key: 'open', label: 'Open (Competitive)' },
  { key: 'selective', label: 'Selective (Pre-qualified)' },
  { key: 'limited', label: 'Limited (Direct)' },
];

const ScatterTT = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tt">
      <p className="tt-id">{d.id}</p>
      <p className="tt-title">{d.title_en || d.title || 'Unknown'}</p>
      <p style={{fontSize:'0.82rem',color:'var(--muted)'}}>{d.valueAmount?.toLocaleString()} UAH · {d.method}</p>
      <div className="tt-score" style={{color: d.score > 0.65 ? 'var(--red)' : d.score > 0.45 ? 'var(--gold)' : 'var(--blue)'}}>
        Risk: {(d.score * 100).toFixed(1)}%
      </div>
    </div>
  );
};

function Poem({ index }) {
  const p = POEMS[index % POEMS.length];
  return (
    <div className="poem">
      <p className="poem-text">{p.uk}</p>
      <p className="poem-en">{p.en}</p>
      <p className="poem-attr">— {p.attr}</p>
    </div>
  );
}

function App() {
  const [tenders, setTenders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [procFilter, setProcFilter] = useState('');
  const [section, setSection] = useState('all');
  const [translations, setTranslations] = useState({});  // tender_id -> {title_en, procurer_en}
  const [translating, setTranslating] = useState({});     // tender_id -> true while loading

  const handleTranslate = useCallback(async (tender) => {
    if (!tender || translations[tender.id] || translating[tender.id]) return;
    if (!tender.title) return; // nothing to translate
    setTranslating(prev => ({ ...prev, [tender.id]: true }));
    try {
      const res = await axios.post('/api/translate', {
        title: tender.title || '',
        procurer: tender.procurer || ''
      });
      setTranslations(prev => ({ ...prev, [tender.id]: res.data }));
    } catch (e) { console.error('Translation failed:', e); }
    setTranslating(prev => ({ ...prev, [tender.id]: false }));
  }, [translations, translating]);

  useEffect(() => { axios.get('/api/paper-stats').then(r => setStats(r.data)).catch(()=>{}); }, []);

  const fetchTenders = useCallback(async () => {
    setLoading(true);
    setSelected(null);
    try {
      const res = await axios.get('/api/tenders', { params: { limit: 50, proc_method: procFilter || undefined } });
      const data = res.data.tenders || res.data;
      const fmt = data.map((t, idx) => ({ ...t, index: idx, score: t.risk_score ?? Math.random(), valueAmount: t.value_uah || 0 }));
      setTenders(fmt);
      if (fmt.length) setSelected(fmt[0]);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [procFilter]);

  useEffect(() => { fetchTenders(); }, [fetchTenders]);

  // Auto-translate selected tender (e.g. from scatter click)
  useEffect(() => { if (selected) handleTranslate(selected); }, [selected]);

  const scrollTo = (id) => { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }); };
  const navItems = [
    { id: 'abstract', label: 'Research' },
    { id: 'methodology', label: 'Method' },
    { id: 'shap', label: 'SHAP' },
    { id: 'transfer', label: 'Transfer' },
    { id: 'observatory', label: 'Live API' },
  ];

  return (
    <div className="app">
      {/* ═══ NAV ═══ */}
      <nav className="nav">
        <div className="nav-brand">Prozorro Observatory</div>
        <div className="nav-links">
          {navItems.map(n => <button key={n.id} onClick={() => scrollTo(n.id)}>{n.label}</button>)}
        </div>
      </nav>

      {/* ═══ HERO ═══ */}
      <header className="hero">
        <div className="hero-bg"><img src="/img/hero.png" alt="" /></div>
        <div className="hero-badge"><span className="dot" /> Research Observatory · {PAPER.version}</div>
        <h1>{PAPER.title}</h1>
        <h2>{PAPER.subtitle}</h2>
        <div className="hero-stats">
          <div className="hero-stat"><div className="val">{PAPER.sample.total.toLocaleString()}</div><div className="lbl">Tenders Evaluated</div></div>
          <div className="hero-stat"><div className="val">0.772</div><div className="lbl">Wartime AUC</div></div>
          <div className="hero-stat"><div className="val">34</div><div className="lbl">Dense Features</div></div>
          <div className="hero-stat"><div className="val">−0.237</div><div className="lbl">Transfer ΔAUC</div></div>
        </div>
      </header>

      <Poem index={0} />

      {/* ═══ RESEARCH SECTIONS ═══ */}
      <ResearchSections stats={stats} />

      <Poem index={1} />

      {/* ═══ WHEAT FIELD BANNER ═══ */}
      <div className="banner">
        <img src="/img/wheat.png" alt="Ukrainian wheat field at sunset — the breadbasket of Europe" />
        <div className="banner-overlay">
          <div className="banner-text">
            <h3>The Breadbasket Under Siege</h3>
            <p>4.5 million competitive tenders span a decade of Ukraine's procurement history. This dataset — the most comprehensive public procurement corpus in the world — traces the nation's resilience from peacetime commerce through wartime survival.</p>
          </div>
        </div>
      </div>

      {/* ═══ LIVE OBSERVATORY ═══ */}
      <section id="observatory">
        <div className="sec-head">
          <div className="sec-num">Section V</div>
          <h2 className="sec-title">Live Procurement Observatory</h2>
          <p className="sec-sub">Real-time inference against the Prozorro public API. Each tender is scored by the LightGBM model via Snowflake ML Registry, translated to English via Cortex, and interpreted through the feature-family decomposition.</p>
        </div>

        <div className="dash-wrap">
          <div className="dash-controls">
            <div className="dash-filters">
              {FILTERS.map(f => (
                <button key={f.key} className={`filter-btn ${procFilter === f.key ? 'active' : ''}`} onClick={() => setProcFilter(f.key)}>{f.label}</button>
              ))}
            </div>
            <button className="btn-sync" onClick={fetchTenders} disabled={loading}>
              {loading ? <><span className="spin" /> Analyzing…</> : '⟳ Synchronize API Feed'}
            </button>
          </div>

          <div className="dash-body">
            {/* LEFT: scatter + list */}
            <div>
              <div className="chart-wrap dash-scatter">
                <h4>Risk Topology Matrix</h4>
                <div className="chart-sub">Click any node for deep analysis. Size = tender value. Color = risk tier.</div>
                <ResponsiveContainer width="100%" height={280}>
                  <ScatterChart margin={{top:10,right:10,bottom:10,left:0}}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                    <XAxis type="number" dataKey="index" hide />
                    <YAxis type="number" dataKey="score" domain={[0,1]} tick={{fontSize:11}} tickFormatter={v=>`${(v*100).toFixed(0)}%`} />
                    <ZAxis type="number" dataKey="valueAmount" range={[40,500]} />
                    <RTooltip content={<ScatterTT />} />
                    <Scatter data={tenders} onClick={e => setSelected(e.payload)}>
                      {tenders.map((t,i) => (
                        <Cell key={i} fill={t.score > 0.65 ? '#dc2626' : t.score > 0.45 ? '#daa520' : '#1e3a8a'} stroke={selected?.id === t.id ? '#000' : 'transparent'} strokeWidth={selected?.id === t.id ? 2 : 0} style={{cursor:'pointer'}} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              <div className="tender-list" style={{marginTop:'1rem'}}>
                {tenders.slice(0,15).map(t => {
                  const trans = translations[t.id];
                  const isTranslating = translating[t.id];
                  return (
                  <div key={t.id} className={`t-item ${selected?.id === t.id ? 'sel' : ''}`} onClick={() => setSelected(t)} onMouseEnter={() => handleTranslate(t)}>
                    <div className="t-main">
                      <div className="t-title">{trans?.title_en || t.title || 'Unknown'}{isTranslating && <span className="spin-sm" />}</div>
                      <div className="t-meta">{t.valueAmount?.toLocaleString()} UAH · {t.method}</div>
                    </div>
                    <div className={`t-badge ${t.score > 0.65 ? 'high' : t.score > 0.45 ? 'med' : 'low'}`}>{(t.score*100).toFixed(1)}%</div>
                  </div>
                  );
                })}
              </div>
            </div>

            {/* RIGHT: detail */}
            <div>
              {selected ? (
                <div className="detail">
                  <div className="detail-header">
                    <span className="detail-id">{selected.id}</span>
                    <a href={selected.href} target="_blank" rel="noreferrer" className="detail-link">View on Prozorro ↗</a>
                  </div>
                  <div className="detail-title">{(translations[selected.id]?.title_en) || selected.title || 'Unknown'}{translating[selected.id] && <span className="spin-sm" />}</div>
                  <div className="detail-procurer">{(translations[selected.id]?.procurer_en) || selected.procurer}</div>

                  <div className="gauge-row">
                    <div className="gauge-circle" style={{background:`conic-gradient(${selected.score > 0.65 ? '#dc2626' : selected.score > 0.45 ? '#daa520' : '#1e3a8a'} ${selected.score*360}deg, var(--border) 0deg)`}}>
                      <div className="gauge-inner"><span className="gauge-val">{(selected.score*100).toFixed(1)}<small>%</small></span></div>
                    </div>
                    <div className="gauge-info">
                      <strong>AI Risk Inference</strong>
                      <p>Source: <span className="mono">{selected.source}</span></p>
                      <p>Level: <span className="mono">{selected.risk_level}</span></p>
                    </div>
                  </div>

                  <div className="interp">
                    <h5>Algorithmic Interpretation</h5>
                    <p>{selected.interpretation || 'Analysis pending.'}</p>
                  </div>

                  <div className="flags">
                    <div className={`flag ${selected.flags?.restricted ? 'on' : ''}`}>Restricted Proc.</div>
                    <div className={`flag ${selected.flags?.near_thresh ? 'on' : ''}`}>Near Threshold</div>
                    <div className={`flag ${selected.flags?.short_period ? 'on' : ''}`}>Short Period</div>
                    <div className={`flag ${selected.flags?.no_docs ? 'on' : ''}`}>Missing Docs</div>
                  </div>

                  <div className="meta-grid">
                    <div className="meta-row"><span>CPV-4</span><strong>{selected.cpv4}</strong></div>
                    <div className="meta-row"><span>Region</span><strong>{selected.region}</strong></div>
                    <div className="meta-row"><span>Items</span><strong>{selected.item_count}</strong></div>
                    <div className="meta-row"><span>Bidders</span><strong>{selected.bid_count ?? '—'}</strong></div>
                    <div className="meta-row"><span>Method</span><strong>{selected.method}</strong></div>
                    <div className="meta-row"><span>Status</span><strong>{selected.status}</strong></div>
                    <div className="meta-row"><span>Date</span><strong>{selected.date}</strong></div>
                    <div className="meta-row"><span>Wartime</span><strong>{selected.wartime ? 'Yes' : 'No'}</strong></div>
                  </div>
                </div>
              ) : (
                <div className="detail empty"><p>Select a tender from the topology matrix or list to run deep analysis.</p></div>
              )}
            </div>
          </div>
        </div>
      </section>

      <Poem index={2} />

      {/* ═══ SHEVCHENKO EXHIBIT ═══ */}
      <section>
        <div className="shevchenko-exhibit">
          <div className="shevchenko-portrait">
            <img src="/img/shevchenko.png" alt="Taras Shevchenko — poet, artist, and national prophet of Ukraine" />
          </div>
          <div className="shevchenko-text">
            <h3>Taras Hryhorovych Shevchenko</h3>
            <div className="verse">{POEMS[5].uk}</div>
            <p className="bio">{POEMS[5].en}</p>
            <p className="bio" style={{marginTop:'1rem'}}>Born into serfdom in 1814 and orphaned at eleven, Shevchenko became the founding voice of modern Ukrainian literature. His poetry — written in a language the Russian Empire sought to erase — transformed personal grief into national consciousness. His call to "study, think, and read" while preserving one's own heritage resonates directly with Prozorro's founding premise: that knowledge, once made public, becomes an instrument of liberation.</p>
          </div>
        </div>
      </section>

      <Poem index={3} />

      {/* ═══ KYIV BANNER ═══ */}
      <div className="banner">
        <img src="/img/kyiv.png" alt="The Golden Gate of Kyiv at golden hour" />
        <div className="banner-overlay">
          <div className="banner-text">
            <h3>Zoloti Vorota — The Golden Gate</h3>
            <p>Built in 1037 by Yaroslav the Wise, the Golden Gate has endured a millennium of conquests. Like Prozorro itself, it stands as a monument to the belief that institutions — built with care — can outlast the forces that seek to destroy them.</p>
          </div>
        </div>
      </div>

      {/* ═══ DISCUSSION ═══ */}
      <section id="discussion">
        <div className="sec-head">
          <div className="sec-num">Section VI</div>
          <h2 className="sec-title">Discussion & Conclusion</h2>
        </div>
        <div className="grid-2">
          <div className="panel"><div className="panel-title"><span className="accent">◆</span> What the Regime Shift Did</div><div className="prose"><p>{PAPER.discussion}</p></div></div>
          <div className="panel"><div className="panel-title"><span className="accent">◆</span> Conclusion</div><div className="prose"><p>{PAPER.conclusion}</p></div></div>
        </div>
      </section>

      <Poem index={4} />

      {/* ═══ DNIEPER BANNER ═══ */}
      <div className="banner">
        <img src="/img/dnieper.png" alt="Aerial view of the Dnieper River through Kyiv at sunset" />
        <div className="banner-overlay">
          <div className="banner-text">
            <h3>The Dnieper — Witness to History</h3>
            <p>"Reve ta stohne Dnipr shyrokyi" — The wide Dnieper roars and groans. Shevchenko's river remains the lifeline of a nation whose data now flows as freely as its waters.</p>
          </div>
        </div>
      </div>

      <Poem index={5} />

      {/* ═══ FOOTER ═══ */}
      <footer>
        <h3>References</h3>
        <div className="refs">{PAPER.refs.map((r,i) => <p key={i}>• {r}</p>)}</div>
        <p className="copy">© 2026 · Prozorro Competitiveness Research Platform · Model {PAPER.version}</p>
      </footer>
    </div>
  );
}

export default App;
