import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Cell } from 'recharts';
import { PAPER } from '../poems';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="tt"><p style={{fontWeight:600,color:'var(--navy)'}}>{label}</p>{payload.map((e,i) => <p key={i} style={{color:e.color}}>{e.name}: <strong>{typeof e.value === 'number' ? e.value.toFixed(3) : e.value}</strong></p>)}</div>);
};

const LEAKAGE_LAYERS = [
  { num:"1", name:"Authoritative Allowlist", desc:"51 pre-tender features explicitly enumerated in allowlisted_columns.yaml" },
  { num:"2", name:"Exhaustive Blacklist", desc:"~45 forbidden columns: WINNING_*, STAT_PRICE_*, SIGNAL_BID_*, all post-award signals" },
  { num:"3", name:"SQL-View Discipline", desc:"F_PRETENDER_BASE uses explicit SELECT list generated from allowlist — no SELECT *" },
  { num:"4", name:"CI Test Suite", desc:"4 tests block CI on any allowlist violation, blacklist appearance, or target-in-features leak" },
  { num:"5", name:"Synthetic Oracle Probe", desc:"Z_SYNTH = y + Gaussian(SNR=2). Max real-feature ratio: 30.6% of oracle importance" },
];

export function ResearchSections() {
  const families = PAPER.families;
  const shapData = families.map(f => ({ name:f.letter, label:f.name, peacetime:f.peace, wartime:f.war }));
  const ablationData = families.filter(f => f.ablationP > 0.005).map(f => ({ name:f.letter, label:f.name, peacetime:-f.ablationP, wartime:-f.ablationW }));
  const allPerf = PAPER.performance;
  const permData = PAPER.permutation.map(p => ({ model:p.model, typology:p.typologyDeltaAuc, random:p.randomMeanDeltaAuc }));

  return (<>
    {/* ══════ ABSTRACT ══════ */}
    <section id="abstract">
      <div className="sec-head">
        <div className="sec-num">Section I</div>
        <h2 className="sec-title">The Scroll of Truth</h2>
        <p className="sec-sub">Abstract & data architecture for 4.54 million competitive tenders across a decade of Ukrainian procurement.</p>
      </div>
      <div className="panel" style={{marginBottom:'2rem'}}>
        <div className="prose" style={{columnCount:2, columnGap:'2.5rem'}}>
          <p>{PAPER.abstract}</p>
          <p>{PAPER.introduction}</p>
        </div>
      </div>
      <div className="grid-4">
        <div className="stat-card gold"><div className="val">{PAPER.sample.total.toLocaleString()}</div><div className="lbl">Tenders Sampled</div></div>
        <div className="stat-card"><div className="val">2016–2026</div><div className="lbl">Temporal Horizon</div></div>
        <div className="stat-card blue"><div className="val">34</div><div className="lbl">Dense Features</div></div>
        <div className="stat-card"><div className="val">11</div><div className="lbl">Feature Families (A–K)</div></div>
      </div>
    </section>

    {/* ══════ SNOWFLAKE BANNER ══════ */}
    <div className="banner">
      <img src="/img/snowflake.png" alt="Snowflake data warehouse visualization" />
      <div className="banner-overlay">
        <div className="banner-text">
          <h3>Snowflake-Resident Data Architecture</h3>
          <p>103 pre-computed columns in the gold feature store, seven dynamic silver tables, and strict as-of-DATE_CREATED temporal discipline — all materialized inside Snowflake for reproducibility.</p>
        </div>
      </div>
    </div>

    {/* ══════ ARCHITECTURE ══════ */}
    <div className="grid-2" style={{margin:'2.5rem 0'}}>
      <div className="arch-diagram">
        <div className="panel-title"><span className="accent">◆</span> Pipeline Architecture (Figure 1)</div>
        <img src="/img/pipeline.png" alt="Pipeline Architecture" />
        <div className="caption">Figure 1. Prozorro API → Snowflake → Three LightGBM Models → SHAP → Live Dashboard</div>
      </div>
      <div className="arch-diagram">
        <div className="panel-title"><span className="accent">◆</span> Feature Family Constellation</div>
        <img src="/img/families.png" alt="Feature families A through K constellation" />
        <div className="caption">11 feature families (A–K) mapped to corruption-typology categories. Node size ∝ peacetime SHAP importance.</div>
      </div>
    </div>

    {/* ══════ METHODOLOGY ══════ */}
    <section id="methodology">
      <div className="sec-head">
        <div className="sec-num">Section II</div>
        <h2 className="sec-title">The Three-Model Design</h2>
        <p className="sec-sub">Three independent classifiers, a five-layer leakage firewall, and 50-trial hyperparameter search per variant.</p>
      </div>
      <div className="grid-2">
        <div>
          <div className="prose"><p>{PAPER.methodology}</p></div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'1rem', marginTop:'2rem'}}>
            {Object.entries(PAPER.splits).map(([regime, s]) => (
              <div key={regime} className="panel" style={{padding:'1.25rem'}}>
                <div style={{fontFamily:'var(--serif)', fontWeight:700, color:'var(--navy)', marginBottom:'0.75rem', textTransform:'capitalize'}}>{regime}</div>
                <div style={{fontSize:'0.8rem', color:'var(--muted)'}}>
                  <div><strong>Train:</strong> {s.train}</div>
                  <div><strong>Val:</strong> {s.val}</div>
                  <div><strong>Test:</strong> {s.test}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="chart-wrap">
          <h4>Model Performance Comparison</h4>
          <div className="chart-sub">Test AUC by algorithm and regime (Table 3)</div>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={allPerf} margin={{top:10,right:10,left:0,bottom:0}}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey={(d) => `${d.model} ${d.algo==='LightGBM'?'(LGB)':d.algo==='Logistic Reg'?'(LR)':'(Rand)'}`} tick={{fontSize:10}} angle={-30} textAnchor="end" height={60} />
              <YAxis domain={[0.4,0.85]} tick={{fontSize:11}} />
              <Tooltip content={<TT />} />
              <Bar dataKey="auc" name="Test AUC" radius={[4,4,0,0]}>
                {allPerf.map((e,i) => <Cell key={i} fill={e.algo==='LightGBM'?(e.model==='Peacetime'?'#3b82f6':e.model==='Wartime'?'#f59e0b':'#10b981'):e.algo==='Logistic Reg'?'#8b5cf6':'#cbd5e1'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* LightGBM Banner */}
      <div className="banner" style={{marginTop:'2.5rem'}}>
        <img src="/img/lightgbm.png" alt="LightGBM gradient boosted decision tree forest visualization" />
        <div className="banner-overlay">
          <div className="banner-text">
            <h3>LightGBM: The Decision Forest</h3>
            <p>500 boosting rounds with early stopping (patience 50), deterministic mode enabled, 50-trial random search independently per variant. Each tree learns the residual signal the ensemble hasn't yet captured.</p>
          </div>
        </div>
      </div>

      {/* Leakage section with image */}
      <div className="grid-2" style={{marginTop:'2.5rem'}}>
        <div>
          <div className="panel-title" style={{marginBottom:'1rem'}}><span className="accent">🔒</span> Five-Layer Leakage Prevention (§4.4)</div>
          <div className="leakage-layers">
            {LEAKAGE_LAYERS.map(l => (
              <div key={l.num} className="leakage-layer">
                <div className="layer-num">{l.num}</div>
                <div className="layer-name">{l.name}</div>
                <div className="layer-desc">{l.desc}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="arch-diagram">
          <img src="/img/firewall.png" alt="Five-layer leakage prevention firewall" style={{borderRadius:'12px'}} />
          <div className="caption">Five concentric barriers protect model integrity: allowlist, blacklist, SQL discipline, CI tests, and synthetic-oracle probe.</div>
        </div>
      </div>

      {/* Contribution Cards */}
      <div className="contrib-grid" style={{marginTop:'2.5rem'}}>
        {PAPER.contributions.map((c,i) => (
          <div key={i} className="contrib-card"><div className="icon">{c.icon}</div><h4>{c.title}</h4><p>{c.body}</p></div>
        ))}
      </div>
    </section>

    {/* ══════ REGIME SHIFT BANNER ══════ */}
    <div className="banner">
      <img src="/img/regime_shift.png" alt="Regime shift: peacetime vs wartime data structure" />
      <div className="banner-overlay">
        <div className="banner-text">
          <h3>The October 2022 Boundary</h3>
          <p>Cabinet Resolution No. 1178 formalized wartime procurement simplification — it did not reduce predictability, but redistributed predictive signal from procedural features onto structural features harder for policy to modify. Single-bidder base rates: 66.2% peacetime, 60.9% wartime.</p>
        </div>
      </div>
    </div>

    {/* ══════ SHAP ══════ */}
    <section id="shap">
      <div className="sec-head">
        <div className="sec-num">Section III</div>
        <h2 className="sec-title">The Redistribution Chamber</h2>
        <p className="sec-sub">Family-level SHAP decomposition reveals structural reorganization of predictive signal.</p>
      </div>

      {/* SHAP waterfall art + chart */}
      <div className="grid-2" style={{marginBottom:'2.5rem'}}>
        <div className="chart-wrap">
          <h4>SHAP Importance by Family</h4>
          <div className="chart-sub">Mean |SHAP| summed per family (Table 4)</div>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart layout="vertical" data={shapData} margin={{top:5,right:20,left:20,bottom:5}}>
              <CartesianGrid strokeDasharray="3 3" horizontal vertical={false} stroke="var(--border)" />
              <XAxis type="number" tick={{fontSize:11}} />
              <YAxis dataKey="name" type="category" tick={{fontSize:12, fontFamily:'var(--mono)'}} width={30} />
              <Tooltip content={<TT />} /><Legend />
              <Bar dataKey="peacetime" name="Peacetime" fill="#3b82f6" barSize={10} radius={[0,4,4,0]} />
              <Bar dataKey="wartime" name="Wartime" fill="#f59e0b" barSize={10} radius={[0,4,4,0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-wrap">
          <h4>Feature Ablation ΔAUC Drop</h4>
          <div className="chart-sub">AUC degradation when each family is nullified (§7.1)</div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart layout="vertical" data={ablationData} margin={{top:5,right:20,left:20,bottom:5}}>
              <CartesianGrid strokeDasharray="3 3" horizontal vertical={false} stroke="var(--border)" />
              <XAxis type="number" tick={{fontSize:11}} />
              <YAxis dataKey="name" type="category" tick={{fontSize:12, fontFamily:'var(--mono)'}} width={30} />
              <Tooltip content={<TT />} /><Legend />
              <Bar dataKey="peacetime" name="Peacetime ΔAUC" fill="#3b82f6" barSize={10} radius={[4,0,0,4]} />
              <Bar dataKey="wartime" name="Wartime ΔAUC" fill="#f59e0b" barSize={10} radius={[4,0,0,4]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SHAP waterfall banner */}
      <div className="banner">
        <img src="/img/shap_waterfall.png" alt="SHAP waterfall visualization" />
        <div className="banner-overlay">
          <div className="banner-text">
            <h3>The SHAP Waterfall</h3>
            <p>Family A cascades with the greatest magnitude. In peacetime it towers at 1.998 mean |SHAP|; in wartime it collapses to 0.877 — a 2.3× redistribution of predictive signal into structural families E, I, and B.</p>
          </div>
        </div>
      </div>

      {/* Family table */}
      <div className="panel" style={{overflow:'auto', marginTop:'2.5rem'}}>
        <div className="panel-title"><span className="accent">◆</span> Master Effect-Size Table (Table 4 + Table 8)</div>
        <table className="family-table">
          <thead><tr><th>Fam</th><th>Name</th><th>N</th><th>Peace</th><th>War</th><th>Δ</th><th>Cohen's d</th><th>KS</th><th>Direction</th></tr></thead>
          <tbody>
            {families.map(f => (
              <tr key={f.letter}>
                <td className="fam-letter">{f.letter}</td><td className="fam-name">{f.name}</td><td className="num">{f.count}</td>
                <td className="num">{f.peace.toFixed(3)}</td><td className="num">{f.war.toFixed(3)}</td>
                <td className={`num ${f.delta>0?'delta-pos':'delta-neg'}`}>{f.delta>0?'+':''}{f.delta.toFixed(3)}</td>
                <td className="num cohen">{f.cohen>0?'+':''}{f.cohen.toFixed(2)}</td><td className="num">{f.ks.toFixed(3)}</td><td className="cohen">{f.direction}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>

    {/* ══════ TRANSPARENCY BANNER ══════ */}
    <div className="banner">
      <img src="/img/shield.png" alt="Anti-corruption shield protecting transparent governance" />
      <div className="banner-overlay">
        <div className="banner-text">
          <h3>Transparency as Anti-Corruption</h3>
          <p>Prozorro's architectural premise: radical publication raises the cost of collusion by exposing it to external scrutiny. The platform's continued operation through wartime constitutes an empirical asset that should be preserved.</p>
        </div>
      </div>
    </div>

    {/* ══════ TRANSFER ══════ */}
    <section id="transfer">
      <div className="sec-head">
        <div className="sec-num">Section IV</div>
        <h2 className="sec-title">Cross-Regime Transfer & Robustness</h2>
        <p className="sec-sub">Asymmetric model transfer reveals genuinely novel wartime predictive structure.</p>
      </div>
      <div className="grid-2">
        <div>
          <div className="prose">
            <p><strong>The transfer asymmetry is dramatic:</strong> peacetime→wartime drops 0.237 AUC (from 0.783 to 0.546), while wartime→peacetime drops only 0.012. The peacetime model fails <strong>~20×</strong> more severely.</p>
            <p>The corrected permutation test (1,000 permutations, feature-count-matched) confirms the typology grouping is privileged in peacetime (p = 0.007) and pooled (p = 0.003), but NOT in wartime (p = 0.066).</p>
          </div>
          <div className="chart-wrap" style={{marginTop:'1.5rem'}}>
            <h4>Permutation Test: Typology vs Random (Table 6b)</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={permData} margin={{top:10,right:10,left:0,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis dataKey="model" tick={{fontSize:12}} /><YAxis tick={{fontSize:11}} />
                <Tooltip content={<TT />} /><Legend />
                <Bar dataKey="typology" name="Typology ΔAUC" fill="var(--gold)" radius={[4,4,0,0]} />
                <Bar dataKey="random" name="Random ΔAUC" fill="#94a3b8" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h4 style={{fontFamily:'var(--serif)', marginBottom:'1rem', color:'var(--navy)'}}>Transfer Matrix (Table 5)</h4>
          <div className="transfer-grid">
            {PAPER.transfer.map((t,i) => (
              <div key={i} className={`transfer-cell ${t.kind==='native'?'native':t.auc<0.7?'degraded':''}`}>
                <div className="cell-label">{t.model} → {t.test}</div>
                <div className="cell-auc" style={{color:t.kind==='native'?'var(--green)':t.auc<0.7?'var(--red)':'var(--navy)'}}>{t.auc.toFixed(3)}</div>
                <div className="cell-label">{t.kind} · N={t.n.toLocaleString()}</div>
                {t.kind==='transfer' && <div className="cell-delta" style={{color:'var(--red)'}}>Δ −{(PAPER.transfer.find(x=>x.model===t.model&&x.kind==='native')?.auc-t.auc).toFixed(3)}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Clusters */}
      <div style={{marginTop:'2.5rem'}}>
        <div className="panel-title"><span className="accent">◆</span> SHAP-Vector Cluster Themes (Table 9)</div>
        <p style={{fontSize:'0.95rem', color:'var(--muted)', marginBottom:'1.5rem'}}>All 10 peacetime clusters are Family-A-dominant. Wartime introduces E, D, and I-dominant clusters — direct corroboration of the SHAP redistribution.</p>
        <div className="cluster-grid">
          {PAPER.clusters.map((c,i) => (
            <div key={i} className="cluster-card">
              <div className="c-variant">{c.variant}</div>
              <div className="c-dom">Fam {c.dominant}</div>
              <div className="c-label">{c.label}</div>
              <div className="c-size">n={c.size.toLocaleString()} · P̄={c.meanPred.toFixed(3)}</div>
            </div>
          ))}
        </div>
      </div>
    </section>

    {/* ══════ API DATA BANNER ══════ */}
    <div className="banner">
      <img src="/img/api_data.png" alt="Prozorro API data stream command center" />
      <div className="banner-overlay">
        <div className="banner-text">
          <h3>Live Prozorro API Stream</h3>
          <p>28.7 million tenders published to a searchable public API. Every tender's documentation, every bid, every award decision — machine-readable, real-time, and open to the world.</p>
        </div>
      </div>
    </div>
  </>);
}
