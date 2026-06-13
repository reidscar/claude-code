import { useState, useEffect, useRef } from "react";

const STEPS = [
  {
    id: 0, name: "Reference Point", icon: "🎯", color: "#D4A843",
    purpose: "Extract and anchor the prospect's desired outcome.",
    science: "Without an anchor, there is no gap. Without a gap, there is no urgency. The prospect's own stated goal becomes the emotional anchor—not the pitch.",
    flag: "REF-POINT MISSING",
    questions: [
      { q: "Where are you trying to be by [quarter/year]?", intent: "Establish specific, time-bound goal" },
      { q: "What number are you personally responsible for?", intent: "Tie goal to personal accountability" },
      { q: "What does a successful 90 days look like?", intent: "Force concrete definition of success" },
    ],
    checks: [
      "Did rep establish a specific, quantified goal first?",
      "Did prospect verbalize success in their own words?",
      "Is reference point anchored to immediate timeline?",
    ],
  },
  {
    id: 1, name: "Current Reality", icon: "📊", color: "#3B82F6",
    purpose: "Surface actual business state with concrete, quantified distance.",
    science: "Status quo bias means familiar pain often beats unfamiliar improvement. The endowment effect means prospects value their current system at ~2.5× its actual worth.",
    flag: "REALITY UNQUANTIFIED",
    questions: [
      { q: "Where are you today against that target?", intent: "Quantify distance from goal" },
      { q: "What's the current run rate?", intent: "Get hard numbers on current performance" },
      { q: "What have you accepted as just 'the way it is'?", intent: "Expose normalized problems" },
      { q: "Target is [X], you're at [Y], so gap is [Z]—right?", intent: "Force them to confirm the math" },
    ],
    checks: [
      "Were specific current-state numbers extracted?",
      "Did rep audit what's currently being done?",
      "Did rep expose what prospect has accepted as normal?",
    ],
  },
  {
    id: 2, name: "Gap Calculator", icon: "📐", color: "#8B5CF6",
    purpose: "Make the gap concrete using prospect's own math, not rep assertions.",
    science: "Once a goal is set, falling short triggers loss-aversion responses. The gap must be expressed in prospect's numbers.",
    flag: "GAP NOT OWNED",
    questions: [
      { q: "So the gap is [Z]—does that track?", intent: "Confirm the math" },
      { q: "What would need to change to close it?", intent: "Make gap visible" },
      { q: "What does that gap affect downstream?", intent: "Attach to consequence" },
      { q: "Is this the gap we need to solve?", intent: "Force ownership" },
    ],
    checks: [
      "Was gap quantifiable?",
      "Did prospect do the math—or did rep state it?",
      "Was gap tied to consequence?",
    ],
    badExample: "You're leaving significant revenue on the table.",
    goodExample: "You said target is 40 qualified meetings/month. You're at 14. That's a 26-meeting gap every month. What does that shortfall do to your sales target?",
  },
  {
    id: 3, name: "Inaction Cost", icon: "⏱️", color: "#EF4444",
    purpose: "Make staying the same more expensive than changing.",
    science: "Loss framing reverses decisions compared to gain framing—even when the math is identical.",
    flag: "INACTION INVISIBLE",
    frames: [
      { name: "Risk", q: "What's riskier—changing the system or keeping the current one another 90 days?" },
      { name: "Goal", q: "Current pace gets you [Y], target is [X]. What has to change?" },
      { name: "Cost", q: "What does the current situation cost in missed revenue, wasted hours, delayed execution?" },
      { name: "Identity", q: "Is this operating system what the company is trying to become?" },
      { name: "Timing", q: "When does this change? What would make it a priority now?" },
    ],
    checks: [
      "Did rep ask 'what happens if nothing changes?'",
      "Did rep surface downstream effects?",
      "Did rep rotate through multiple frames?",
      "Was cost stated by prospect—not asserted by rep?",
    ],
  },
  {
    id: 4, name: "Reframe & Position", icon: "🔄", color: "#27AE60",
    purpose: "Position solution as loss prevention, not spending.",
    science: "A $50K fee is rational when measured against a $200K gap cost (~4× weight due to loss asymmetry).",
    flag: "PREMATURE CLOSE",
    reframes: [
      { objection: "Price feels high", response: "Compared to what—the current cost of the gap?" },
      { objection: "Not the right time", response: "When does the gap become expensive enough?" },
      { objection: "Need to think about it", response: "What part of the math doesn't work?" },
      { objection: "Looking at other options", response: "What are those options solving that this doesn't?" },
    ],
    checks: [
      "Was price introduced before gap was visible?",
      "Was offer positioned as loss prevention?",
      "Did rep tie price to gap economics?",
    ],
  },
];

const OBJECTIONS = [
  { say: "Too expensive", means: "Doubt execution, not affordability", move: "Compared to what—cost of the gap?" },
  { say: "Need to think", means: "Gap not fully owned", move: "What part is unclear?" },
  { say: "Tried before", means: "Past failure anxiety", move: "What happened? What outcome vs. expected?" },
  { say: "Send info first", means: "Not ready or testing", move: "What specifically helps you decide if worth continuing?" },
  { say: "Not the right time", means: "Inaction cost not real enough", move: "When would it be? What changes?" },
  { say: "Looking at options", means: "Internal uncertainty", move: "What are those solving that this doesn't?" },
  { say: "Silence after interest", means: "Approval confusion or bureaucracy", move: "One value-add message (no reply needed), then single micro-step CTA" },
];

const MEDDPICC = [
  { letter: "M", name: "Metrics", desc: "Quantified success criteria", q: "What does success look like in numbers?" },
  { letter: "E", name: "Economic Buyer", desc: "Who signs the check", q: "Who signs off on a commitment this size?" },
  { letter: "D", name: "Decision Criteria", desc: "How they evaluate options", q: "Three most important things this must do?" },
  { letter: "D", name: "Decision Process", desc: "Steps to agreement", q: "Walk me through the internal path forward." },
  { letter: "P", name: "Paper Process", desc: "Legal/procurement path", q: "Procurement or legal review involved?" },
  { letter: "I", name: "Identified Pain", desc: "The quantified gap", q: "What is the cost of this problem right now?" },
  { letter: "C", name: "Champion", desc: "Internal advocate", q: "Who is affected most positively internally?" },
  { letter: "C", name: "Competition", desc: "Other options in play", q: "What else are you looking at?" },
];

const CLOSE_CHECKLIST = [
  "Reference point established + confirmed",
  "Gap quantified + owned by prospect",
  "Inaction cost surfaced across 2+ frames",
  "At least 1 strong admission captured",
  "Fingerprints on scope (they edited/gave feedback)",
  "Champion identified + can articulate internal case",
  "Economic buyer path understood",
];

const AnimatedCounter = ({ value, suffix = "" }) => {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = display;
    let startTime = null;
    const animate = (ts) => {
      if (!startTime) startTime = ts;
      const p = Math.min((ts - startTime) / 800, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(start + (value - start) * eased));
      if (p < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [value]);
  return <span>{display.toLocaleString()}{suffix}</span>;
};

function GapCalculatorTool() {
  const [target, setTarget] = useState("");
  const [current, setCurrent] = useState("");
  const [period, setPeriod] = useState("month");
  const [unit, setUnit] = useState("revenue");

  const t = parseInt(target.replace(/[^0-9]/g, "")) || 0;
  const c = parseInt(current.replace(/[^0-9]/g, "")) || 0;
  const gap = t - c;
  const gapPercent = t > 0 ? Math.round((gap / t) * 100) : 0;
  const annualGap = period === "month" ? gap * 12 : period === "quarter" ? gap * 4 : gap;
  const isRevenue = unit === "revenue";
  const prefix = isRevenue ? "$" : "";
  const suffix = isRevenue ? "" : ` ${unit}`;

  return (
    <div style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.15)", borderRadius: "16px", padding: "28px" }}>
      <h3 style={{ color: "#8B5CF6", fontSize: "14px", letterSpacing: "1.5px", textTransform: "uppercase", marginBottom: "20px" }}>
        Interactive Gap Calculator
      </h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
        <div>
          <label style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>Metric Type</label>
          <select value={unit} onChange={e => setUnit(e.target.value)} style={selectStyle}>
            <option value="revenue">Revenue ($)</option>
            <option value="leads">Leads</option>
            <option value="meetings">Meetings</option>
            <option value="conversions">Conversions</option>
            <option value="units">Units</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>Period</label>
          <select value={period} onChange={e => setPeriod(e.target.value)} style={selectStyle}>
            <option value="month">Per Month</option>
            <option value="quarter">Per Quarter</option>
            <option value="year">Per Year</option>
          </select>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "20px" }}>
        <div>
          <label style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>Reference Point (Target)</label>
          <input type="text" placeholder={isRevenue ? "$500,000" : "40"} value={target}
            onChange={e => { const r = e.target.value.replace(/[^0-9]/g, ""); setTarget(r ? parseInt(r).toLocaleString() : ""); }}
            style={inputStyle} />
        </div>
        <div>
          <label style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>Current Reality</label>
          <input type="text" placeholder={isRevenue ? "$200,000" : "14"} value={current}
            onChange={e => { const r = e.target.value.replace(/[^0-9]/g, ""); setCurrent(r ? parseInt(r).toLocaleString() : ""); }}
            style={inputStyle} />
        </div>
      </div>
      {t > 0 && c > 0 && gap > 0 && (
        <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: "12px", padding: "24px", textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#8B5CF6", textTransform: "uppercase", letterSpacing: "2px", marginBottom: "8px" }}>The Gap</p>
          <div style={{ fontSize: "36px", fontWeight: 800, color: "#EF4444", marginBottom: "4px" }}>
            {prefix}<AnimatedCounter value={gap} />{suffix}
          </div>
          <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
            {gapPercent}% below target per {period}
          </p>
          {period !== "year" && (
            <div style={{ background: "rgba(239,68,68,0.1)", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
              <p style={{ fontSize: "11px", color: "#ef4444", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px" }}>Annualized Cost of Inaction</p>
              <p style={{ fontSize: "24px", fontWeight: 700, color: "#ef4444" }}>
                {prefix}<AnimatedCounter value={annualGap} />{suffix}
              </p>
            </div>
          )}
          <div style={{ background: "rgba(139,92,246,0.1)", borderRadius: "8px", padding: "14px", textAlign: "left" }}>
            <p style={{ fontSize: "12px", fontWeight: 600, color: "#8B5CF6", marginBottom: "8px" }}>Say this to the prospect:</p>
            <p style={{ fontSize: "14px", color: "#e2e8f0", fontStyle: "italic", lineHeight: 1.6 }}>
              "You said your target is {prefix}{t.toLocaleString()}{suffix} per {period}. You're at {prefix}{c.toLocaleString()}{suffix}. That's a {prefix}{gap.toLocaleString()}{suffix} gap every {period}.
              {period !== "year" ? ` That's ${prefix}${annualGap.toLocaleString()}${suffix} per year you're leaving behind.` : ""} What does that shortfall affect downstream?"
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function CloseReadiness() {
  const [checks, setChecks] = useState(CLOSE_CHECKLIST.map(() => false));
  const score = checks.filter(Boolean).length;
  const total = checks.length;
  const pct = Math.round((score / total) * 100);
  const ready = score >= 6;

  return (
    <div style={{ background: "rgba(39,174,96,0.06)", border: "1px solid rgba(39,174,96,0.15)", borderRadius: "16px", padding: "28px" }}>
      <h3 style={{ color: "#27AE60", fontSize: "14px", letterSpacing: "1.5px", textTransform: "uppercase", marginBottom: "20px" }}>
        Close Readiness Scorecard
      </h3>
      <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "24px" }}>
        <div style={{
          width: "80px", height: "80px", borderRadius: "50%",
          background: `conic-gradient(${ready ? "#27ae60" : "#D4A843"} ${pct * 3.6}deg, rgba(255,255,255,0.05) 0deg)`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{ width: "64px", height: "64px", borderRadius: "50%", background: "#0a0f1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: "20px", fontWeight: 800, color: ready ? "#27ae60" : "#D4A843" }}>{score}/{total}</span>
          </div>
        </div>
        <div>
          <p style={{ fontSize: "18px", fontWeight: 700, color: ready ? "#27ae60" : "#D4A843" }}>
            {ready ? "Ready to Close" : score >= 4 ? "Almost There" : "Not Ready"}
          </p>
          <p style={{ fontSize: "13px", color: "#94a3b8" }}>
            {ready ? "Push-to-close signal: prospect stops suggesting changes, starts asking 'what's next?'" : `Complete ${total - score} more item${total - score > 1 ? "s" : ""} before pushing to close.`}
          </p>
        </div>
      </div>
      {CLOSE_CHECKLIST.map((item, i) => (
        <label key={i} style={{
          display: "flex", alignItems: "center", gap: "12px", padding: "10px 12px", cursor: "pointer",
          borderRadius: "8px", marginBottom: "4px",
          background: checks[i] ? "rgba(39,174,96,0.08)" : "transparent",
          transition: "background 0.2s",
        }}>
          <input type="checkbox" checked={checks[i]}
            onChange={() => { const n = [...checks]; n[i] = !n[i]; setChecks(n); }}
            style={{ accentColor: "#27ae60", width: "16px", height: "16px" }} />
          <span style={{ fontSize: "14px", color: checks[i] ? "#27ae60" : "#94a3b8" }}>{item}</span>
        </label>
      ))}
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: "12px 14px", borderRadius: "10px",
  border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)",
  color: "#fff", fontSize: "16px", fontWeight: 600, outline: "none", boxSizing: "border-box",
  marginTop: "6px",
};

const selectStyle = {
  ...inputStyle, appearance: "none", cursor: "pointer",
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2394a3b8' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E")`,
  backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center",
};

export default function GapSiApp() {
  const [activeTab, setActiveTab] = useState("framework");
  const [expandedStep, setExpandedStep] = useState(null);
  const [expandedObj, setExpandedObj] = useState(null);
  const [meddChecks, setMeddChecks] = useState(MEDDPICC.map(() => false));

  const tabs = [
    { id: "framework", label: "5-Step Framework", icon: "🔬" },
    { id: "calculator", label: "Gap Calculator", icon: "📐" },
    { id: "objections", label: "Objection Doctrine", icon: "🛡️" },
    { id: "meddpicc", label: "MEDDPICC", icon: "🗺️" },
    { id: "close", label: "Close Readiness", icon: "✅" },
  ];

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(145deg, #0a0f1a 0%, #111827 40%, #0d1520 100%)",
      fontFamily: "'Instrument Sans', 'SF Pro Display', -apple-system, sans-serif",
      color: "#e2e8f0",
    }}>
      <div style={{ position: "fixed", top: "-20%", right: "-10%", width: "600px", height: "600px", background: "radial-gradient(circle, rgba(212,168,67,0.06) 0%, transparent 70%)", pointerEvents: "none" }} />
      <div style={{ position: "fixed", bottom: "-20%", left: "-10%", width: "500px", height: "500px", background: "radial-gradient(circle, rgba(139,92,246,0.04) 0%, transparent 70%)", pointerEvents: "none" }} />

      <div style={{ maxWidth: "760px", margin: "0 auto", padding: "40px 24px", position: "relative" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "36px" }}>
          <div style={{ display: "inline-block", padding: "6px 16px", border: "1px solid rgba(212,168,67,0.3)", borderRadius: "100px", fontSize: "11px", letterSpacing: "2px", textTransform: "uppercase", color: "#D4A843", marginBottom: "20px" }}>
            GapSi &middot; Sales Intelligence
          </div>
          <h1 style={{ fontSize: "clamp(28px, 5vw, 42px)", fontWeight: 700, lineHeight: 1.15, margin: "0 0 14px", background: "linear-gradient(135deg, #ffffff 0%, #D4A843 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            B2B Sales Intelligence<br />Framework
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: 1.6, maxWidth: "520px", margin: "0 auto" }}>
            Built on Kahneman &amp; Tversky's Prospect Theory. Losses feel 2&times; as painful as equivalent gains.
            Make staying the same more expensive than changing.
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: "flex", gap: "6px", marginBottom: "28px", overflowX: "auto", paddingBottom: "4px" }}>
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
              padding: "10px 16px", borderRadius: "10px", border: "none", cursor: "pointer",
              background: activeTab === tab.id ? "rgba(212,168,67,0.15)" : "rgba(255,255,255,0.03)",
              color: activeTab === tab.id ? "#D4A843" : "#64748b",
              fontSize: "13px", fontWeight: 600, whiteSpace: "nowrap", transition: "all 0.2s",
              borderBottom: activeTab === tab.id ? "2px solid #D4A843" : "2px solid transparent",
            }}>
              <span style={{ marginRight: "6px" }}>{tab.icon}</span>{tab.label}
            </button>
          ))}
        </div>

        {/* Framework Tab */}
        {activeTab === "framework" && (
          <div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {STEPS.map((step) => (
                <div key={step.id} style={{
                  background: "rgba(255,255,255,0.03)", border: `1px solid ${expandedStep === step.id ? step.color + "40" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: "16px", overflow: "hidden", transition: "border-color 0.3s",
                }}>
                  <button onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)} style={{
                    width: "100%", padding: "20px 24px", background: "none", border: "none", cursor: "pointer",
                    display: "flex", alignItems: "center", gap: "16px", textAlign: "left",
                  }}>
                    <div style={{
                      width: "44px", height: "44px", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center",
                      background: step.color + "15", fontSize: "22px", flexShrink: 0,
                    }}>{step.icon}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "11px", color: step.color, fontWeight: 700 }}>STEP {step.id}</span>
                        <span style={{ fontSize: "16px", fontWeight: 700, color: "#e2e8f0" }}>{step.name}</span>
                      </div>
                      <p style={{ fontSize: "13px", color: "#94a3b8", margin: "4px 0 0" }}>{step.purpose}</p>
                    </div>
                    <span style={{ color: "#64748b", fontSize: "18px", transition: "transform 0.2s", transform: expandedStep === step.id ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
                  </button>

                  {expandedStep === step.id && (
                    <div style={{ padding: "0 24px 24px" }}>
                      <div style={{ background: step.color + "10", borderRadius: "10px", padding: "14px 16px", marginBottom: "16px", borderLeft: `3px solid ${step.color}` }}>
                        <p style={{ fontSize: "12px", fontWeight: 600, color: step.color, marginBottom: "4px" }}>Behavioral Science</p>
                        <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.6 }}>{step.science}</p>
                      </div>

                      {step.questions && (
                        <div style={{ marginBottom: "16px" }}>
                          <p style={{ fontSize: "12px", fontWeight: 600, color: step.color, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>Key Questions</p>
                          {step.questions.map((q, i) => (
                            <div key={i} style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "8px", marginBottom: "6px" }}>
                              <p style={{ fontSize: "14px", color: "#e2e8f0", fontStyle: "italic" }}>"{q.q}"</p>
                              <p style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>{q.intent}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {step.frames && (
                        <div style={{ marginBottom: "16px" }}>
                          <p style={{ fontSize: "12px", fontWeight: 600, color: step.color, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>Five-Frame Rotation</p>
                          {step.frames.map((f, i) => (
                            <div key={i} style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "8px", marginBottom: "6px", display: "flex", gap: "12px", alignItems: "flex-start" }}>
                              <span style={{ fontSize: "11px", fontWeight: 700, color: step.color, background: step.color + "20", padding: "2px 8px", borderRadius: "4px", whiteSpace: "nowrap" }}>{f.name}</span>
                              <p style={{ fontSize: "13px", color: "#e2e8f0", fontStyle: "italic" }}>"{f.q}"</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {step.reframes && (
                        <div style={{ marginBottom: "16px" }}>
                          <p style={{ fontSize: "12px", fontWeight: 600, color: step.color, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "10px" }}>Reframe Language</p>
                          {step.reframes.map((r, i) => (
                            <div key={i} style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "8px", marginBottom: "6px" }}>
                              <p style={{ fontSize: "12px", color: "#ef4444" }}>They say: "{r.objection}"</p>
                              <p style={{ fontSize: "14px", color: "#27ae60", fontWeight: 600, marginTop: "4px" }}>→ "{r.response}"</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {step.goodExample && (
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
                          <div style={{ padding: "12px", background: "rgba(239,68,68,0.08)", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.15)" }}>
                            <p style={{ fontSize: "11px", color: "#ef4444", fontWeight: 600, marginBottom: "6px" }}>BAD</p>
                            <p style={{ fontSize: "13px", color: "#94a3b8", fontStyle: "italic" }}>"{step.badExample}"</p>
                          </div>
                          <div style={{ padding: "12px", background: "rgba(39,174,96,0.08)", borderRadius: "8px", border: "1px solid rgba(39,174,96,0.15)" }}>
                            <p style={{ fontSize: "11px", color: "#27ae60", fontWeight: 600, marginBottom: "6px" }}>GOOD</p>
                            <p style={{ fontSize: "13px", color: "#94a3b8", fontStyle: "italic" }}>"{step.goodExample}"</p>
                          </div>
                        </div>
                      )}

                      <div>
                        <p style={{ fontSize: "12px", fontWeight: 600, color: "#ef4444", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                          Diagnostic Check — Flag: {step.flag}
                        </p>
                        {step.checks.map((ch, i) => (
                          <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0" }}>
                            <span style={{ fontSize: "10px", color: step.color }}>●</span>
                            <span style={{ fontSize: "13px", color: "#94a3b8" }}>{ch}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Calculator Tab */}
        {activeTab === "calculator" && <GapCalculatorTool />}

        {/* Objections Tab */}
        {activeTab === "objections" && (
          <div>
            <div style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)", borderRadius: "12px", padding: "16px 20px", marginBottom: "20px" }}>
              <p style={{ fontSize: "14px", fontWeight: 600, color: "#ef4444" }}>Core Rule: Never rebut. Answer every objection with a question.</p>
              <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>Objections reveal which of the 5 steps wasn't completed.</p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {OBJECTIONS.map((obj, i) => (
                <div key={i} onClick={() => setExpandedObj(expandedObj === i ? null : i)} style={{
                  background: "rgba(255,255,255,0.03)", border: `1px solid ${expandedObj === i ? "rgba(212,168,67,0.3)" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: "12px", padding: "16px 20px", cursor: "pointer", transition: "all 0.2s",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p style={{ fontSize: "15px", fontWeight: 600, color: "#e2e8f0" }}>"{obj.say}"</p>
                    <span style={{ color: "#64748b", fontSize: "14px", transition: "transform 0.2s", transform: expandedObj === i ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
                  </div>
                  {expandedObj === i && (
                    <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                      <div style={{ marginBottom: "10px" }}>
                        <p style={{ fontSize: "11px", color: "#D4A843", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px" }}>What it really means</p>
                        <p style={{ fontSize: "14px", color: "#94a3b8" }}>{obj.means}</p>
                      </div>
                      <div style={{ background: "rgba(39,174,96,0.08)", borderRadius: "8px", padding: "12px 14px" }}>
                        <p style={{ fontSize: "11px", color: "#27ae60", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px" }}>Your move</p>
                        <p style={{ fontSize: "15px", fontWeight: 600, color: "#27ae60", fontStyle: "italic" }}>"{obj.move}"</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* MEDDPICC Tab */}
        {activeTab === "meddpicc" && (
          <div>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px" }}>
              Track decision maker mapping across every deal. Check off components as they're confirmed.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {MEDDPICC.map((item, i) => (
                <label key={i} style={{
                  display: "flex", gap: "16px", alignItems: "flex-start", padding: "16px 20px",
                  background: meddChecks[i] ? "rgba(39,174,96,0.06)" : "rgba(255,255,255,0.03)",
                  border: `1px solid ${meddChecks[i] ? "rgba(39,174,96,0.15)" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: "12px", cursor: "pointer", transition: "all 0.2s",
                }}>
                  <input type="checkbox" checked={meddChecks[i]}
                    onChange={() => { const n = [...meddChecks]; n[i] = !n[i]; setMeddChecks(n); }}
                    style={{ accentColor: "#27ae60", width: "18px", height: "18px", marginTop: "2px", flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{
                        fontSize: "13px", fontWeight: 800, color: "#D4A843",
                        background: "rgba(212,168,67,0.15)", padding: "2px 8px", borderRadius: "4px",
                      }}>{item.letter}</span>
                      <span style={{ fontSize: "15px", fontWeight: 600, color: meddChecks[i] ? "#27ae60" : "#e2e8f0" }}>{item.name}</span>
                    </div>
                    <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "6px" }}>{item.desc}</p>
                    <div style={{ background: "rgba(0,0,0,0.15)", borderRadius: "6px", padding: "8px 12px" }}>
                      <p style={{ fontSize: "13px", color: "#94a3b8", fontStyle: "italic" }}>"{item.q}"</p>
                    </div>
                  </div>
                </label>
              ))}
            </div>
            <div style={{ textAlign: "center", marginTop: "20px", padding: "16px", background: "rgba(212,168,67,0.06)", borderRadius: "12px" }}>
              <p style={{ fontSize: "24px", fontWeight: 800, color: "#D4A843" }}>
                {meddChecks.filter(Boolean).length} / {MEDDPICC.length}
              </p>
              <p style={{ fontSize: "13px", color: "#94a3b8" }}>Components confirmed</p>
            </div>
          </div>
        )}

        {/* Close Readiness Tab */}
        {activeTab === "close" && <CloseReadiness />}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: "48px", paddingTop: "24px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <p style={{ fontSize: "11px", color: "#475569" }}>
            GapSi &middot; Gap + Sales Intelligence &middot; Built on Prospect Theory (Kahneman &amp; Tversky, 1979)
          </p>
        </div>
      </div>
    </div>
  );
}
