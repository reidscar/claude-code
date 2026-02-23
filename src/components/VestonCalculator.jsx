import { useState, useEffect, useRef } from "react";

const COUNTRIES = [
  { name: "United Kingdom", flag: "\u{1F1EC}\u{1F1E7}", taxLow: 40, taxHigh: 55, treaty: true, currency: "\u00A3" },
  { name: "Germany", flag: "\u{1F1E9}\u{1F1EA}", taxLow: 42, taxHigh: 47, treaty: true, currency: "\u20AC" },
  { name: "France", flag: "\u{1F1EB}\u{1F1F7}", taxLow: 41, taxHigh: 45, treaty: true, currency: "\u20AC" },
  { name: "Netherlands", flag: "\u{1F1F3}\u{1F1F1}", taxLow: 37, taxHigh: 49, treaty: true, currency: "\u20AC" },
  { name: "India", flag: "\u{1F1EE}\u{1F1F3}", taxLow: 30, taxHigh: 42, treaty: true, currency: "\u20B9" },
  { name: "Pakistan", flag: "\u{1F1F5}\u{1F1F0}", taxLow: 29, taxHigh: 35, treaty: true, currency: "Rs" },
  { name: "South Africa", flag: "\u{1F1FF}\u{1F1E6}", taxLow: 27, taxHigh: 45, treaty: true, currency: "R" },
  { name: "Nigeria", flag: "\u{1F1F3}\u{1F1EC}", taxLow: 24, taxHigh: 30, treaty: true, currency: "\u20A6" },
  { name: "Egypt", flag: "\u{1F1EA}\u{1F1EC}", taxLow: 22, taxHigh: 25, treaty: true, currency: "E\u00A3" },
  { name: "Kenya", flag: "\u{1F1F0}\u{1F1EA}", taxLow: 25, taxHigh: 30, treaty: true, currency: "KSh" },
  { name: "Canada", flag: "\u{1F1E8}\u{1F1E6}", taxLow: 38, taxHigh: 53, treaty: true, currency: "C$" },
  { name: "Australia", flag: "\u{1F1E6}\u{1F1FA}", taxLow: 30, taxHigh: 47, treaty: true, currency: "A$" },
  { name: "Italy", flag: "\u{1F1EE}\u{1F1F9}", taxLow: 35, taxHigh: 43, treaty: true, currency: "\u20AC" },
  { name: "Spain", flag: "\u{1F1EA}\u{1F1F8}", taxLow: 30, taxHigh: 47, treaty: true, currency: "\u20AC" },
  { name: "Poland", flag: "\u{1F1F5}\u{1F1F1}", taxLow: 32, taxHigh: 41, treaty: true, currency: "z\u0142" },
  { name: "Other Treaty Country", flag: "\u{1F30D}", taxLow: 25, taxHigh: 45, treaty: true, currency: "\u00A3" },
];

const fmt = (n, c = "\u00A3") => {
  if (n >= 1000000) return `${c}${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${c}${Math.round(n).toLocaleString()}`;
  return `${c}${Math.round(n)}`;
};

const AnimatedNumber = ({ value, currency = "\u00A3", duration = 800 }) => {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = display;
    let startTime = null;
    const animate = (ts) => {
      if (!startTime) startTime = ts;
      const p = Math.min((ts - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(start + (value - start) * eased));
      if (p < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [value]);
  return <span>{fmt(display, currency)}</span>;
};

export default function VestonCalculator() {
  const [step, setStep] = useState(0);
  const [country, setCountry] = useState(null);
  const [revenue, setRevenue] = useState("");
  const [taxRate, setTaxRate] = useState(40);
  const [showResults, setShowResults] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const rev = parseInt(revenue.replace(/[^0-9]/g, "")) || 0;
  const cur = country?.currency || "\u00A3";

  // Calculations
  const currentTax = Math.round(rev * (taxRate / 100));
  const uaeTax = Math.round(rev * 0.09);
  const vestonFee = Math.round(rev * 0.08);
  const admin = Math.min(Math.round(rev * 0.02), 6000);
  const totalPoem = uaeTax + vestonFee + admin;
  const annualSaving = currentTax - totalPoem;
  const monthlySaving = Math.round(annualSaving / 12);
  const setupCost = 20000;
  const paybackMonths = annualSaving > 0 ? Math.ceil(setupCost / monthlySaving) : 99;
  const savingPercent = rev > 0 ? Math.round((annualSaving / rev) * 100) : 0;

  const handleCalculate = () => {
    if (rev >= 100000 && country) {
      setShowResults(true);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(145deg, #0a0f1a 0%, #111827 40%, #0d1520 100%)",
      fontFamily: "'Instrument Sans', 'SF Pro Display', -apple-system, sans-serif",
      color: "#e2e8f0",
      padding: "0",
      overflow: "hidden",
      position: "relative",
    }}>
      {/* Ambient glow */}
      <div style={{
        position: "fixed", top: "-20%", right: "-10%", width: "600px", height: "600px",
        background: "radial-gradient(circle, rgba(212,168,67,0.06) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />
      <div style={{
        position: "fixed", bottom: "-20%", left: "-10%", width: "500px", height: "500px",
        background: "radial-gradient(circle, rgba(39,174,96,0.04) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <div style={{ maxWidth: "680px", margin: "0 auto", padding: "40px 24px", position: "relative" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <div style={{
            display: "inline-block",
            padding: "6px 16px",
            border: "1px solid rgba(212,168,67,0.3)",
            borderRadius: "100px",
            fontSize: "11px",
            letterSpacing: "2px",
            textTransform: "uppercase",
            color: "#D4A843",
            marginBottom: "24px",
          }}>
            Veston Partners
          </div>
          <h1 style={{
            fontSize: "clamp(28px, 5vw, 42px)",
            fontWeight: 700,
            lineHeight: 1.15,
            margin: "0 0 16px",
            background: "linear-gradient(135deg, #ffffff 0%, #D4A843 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>
            International Structuring<br />Savings Calculator
          </h1>
          <p style={{
            fontSize: "15px",
            color: "#94a3b8",
            lineHeight: 1.6,
            maxWidth: "480px",
            margin: "0 auto",
          }}>
            See what your business could retain through a treaty-compliant UAE treasury structure. No relocation required.
          </p>
        </div>

        {!showResults ? (
          <div style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: "20px",
            padding: "36px 32px",
            backdropFilter: "blur(20px)",
          }}>
            {/* Country Selection */}
            <div style={{ marginBottom: "32px" }}>
              <label style={{
                display: "block", fontSize: "12px", letterSpacing: "1.5px",
                textTransform: "uppercase", color: "#D4A843", marginBottom: "14px", fontWeight: 600,
              }}>
                Your Country
              </label>
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: "8px",
              }}>
                {COUNTRIES.map((c) => (
                  <button
                    key={c.name}
                    onClick={() => {
                      setCountry(c);
                      setTaxRate(Math.round((c.taxLow + c.taxHigh) / 2));
                    }}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "10px",
                      border: country?.name === c.name
                        ? "1.5px solid #D4A843"
                        : "1px solid rgba(255,255,255,0.08)",
                      background: country?.name === c.name
                        ? "rgba(212,168,67,0.1)"
                        : "rgba(255,255,255,0.02)",
                      color: country?.name === c.name ? "#D4A843" : "#94a3b8",
                      cursor: "pointer",
                      fontSize: "13px",
                      fontWeight: 500,
                      textAlign: "left",
                      transition: "all 0.2s",
                    }}
                  >
                    <span style={{ marginRight: "6px" }}>{c.flag}</span>
                    {c.name.length > 14 ? c.name.slice(0, 14) + "\u2026" : c.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Revenue Input */}
            <div style={{ marginBottom: "28px" }}>
              <label style={{
                display: "block", fontSize: "12px", letterSpacing: "1.5px",
                textTransform: "uppercase", color: "#D4A843", marginBottom: "10px", fontWeight: 600,
              }}>
                Annual Revenue ({cur})
              </label>
              <input
                type="text"
                placeholder={`e.g. ${cur}300,000`}
                value={revenue}
                onChange={(e) => {
                  const raw = e.target.value.replace(/[^0-9]/g, "");
                  if (raw) {
                    setRevenue(parseInt(raw).toLocaleString());
                  } else {
                    setRevenue("");
                  }
                }}
                style={{
                  width: "100%",
                  padding: "14px 18px",
                  borderRadius: "12px",
                  border: "1px solid rgba(255,255,255,0.1)",
                  background: "rgba(255,255,255,0.04)",
                  color: "#fff",
                  fontSize: "18px",
                  fontWeight: 600,
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => e.target.style.borderColor = "rgba(212,168,67,0.5)"}
                onBlur={(e) => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
              />
              {rev > 0 && rev < 100000 && (
                <p style={{ fontSize: "12px", color: "#ef4444", marginTop: "8px" }}>
                  Minimum revenue for PoEM structure: {cur}100,000
                </p>
              )}
            </div>

            {/* Tax Rate Slider */}
            {country && (
              <div style={{ marginBottom: "32px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <label style={{
                    fontSize: "12px", letterSpacing: "1.5px",
                    textTransform: "uppercase", color: "#D4A843", fontWeight: 600,
                  }}>
                    Current Effective Tax Rate
                  </label>
                  <span style={{
                    fontSize: "20px", fontWeight: 700, color: "#ef4444",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    {taxRate}%
                  </span>
                </div>
                <input
                  type="range"
                  min={Math.max(country.taxLow - 5, 15)}
                  max={Math.min(country.taxHigh + 5, 60)}
                  value={taxRate}
                  onChange={(e) => setTaxRate(parseInt(e.target.value))}
                  style={{
                    width: "100%",
                    height: "6px",
                    borderRadius: "3px",
                    appearance: "none",
                    background: `linear-gradient(to right, #D4A843 0%, #ef4444 100%)`,
                    outline: "none",
                    cursor: "pointer",
                  }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  <span>{country.name} range: {country.taxLow}%</span>
                  <span>{country.taxHigh}%</span>
                </div>
              </div>
            )}

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={!country || rev < 100000}
              style={{
                width: "100%",
                padding: "16px",
                borderRadius: "12px",
                border: "none",
                background: (!country || rev < 100000)
                  ? "rgba(255,255,255,0.05)"
                  : "linear-gradient(135deg, #D4A843 0%, #b8912e 100%)",
                color: (!country || rev < 100000) ? "#64748b" : "#0a0f1a",
                fontSize: "15px",
                fontWeight: 700,
                letterSpacing: "0.5px",
                cursor: (!country || rev < 100000) ? "default" : "pointer",
                transition: "all 0.3s",
                textTransform: "uppercase",
              }}
            >
              Calculate My Savings
            </button>
          </div>
        ) : (
          /* RESULTS */
          <div>
            {/* Hero saving */}
            <div style={{
              textAlign: "center",
              padding: "40px 24px",
              background: "rgba(39,174,96,0.06)",
              border: "1px solid rgba(39,174,96,0.15)",
              borderRadius: "20px",
              marginBottom: "24px",
            }}>
              <p style={{ fontSize: "12px", letterSpacing: "2px", textTransform: "uppercase", color: "#27ae60", marginBottom: "8px", fontWeight: 600 }}>
                Estimated Annual Improvement in Retained Capital
              </p>
              <div style={{
                fontSize: "clamp(40px, 8vw, 56px)",
                fontWeight: 800,
                color: "#27ae60",
                lineHeight: 1.1,
                marginBottom: "8px",
              }}>
                <AnimatedNumber value={annualSaving} currency={cur} />
              </div>
              <p style={{ fontSize: "14px", color: "#94a3b8" }}>
                {fmt(monthlySaving, cur)}/month &middot; {savingPercent}% of revenue &middot; Payback in {paybackMonths} months
              </p>
            </div>

            {/* Comparison */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              marginBottom: "24px",
            }}>
              {/* Current */}
              <div style={{
                padding: "24px 20px",
                background: "rgba(239,68,68,0.06)",
                border: "1px solid rgba(239,68,68,0.15)",
                borderRadius: "16px",
              }}>
                <p style={{ fontSize: "11px", letterSpacing: "1.5px", textTransform: "uppercase", color: "#ef4444", marginBottom: "16px", fontWeight: 600 }}>
                  Current ({country.name})
                </p>
                <div style={{ fontSize: "28px", fontWeight: 700, color: "#ef4444", marginBottom: "4px" }}>
                  <AnimatedNumber value={currentTax} currency={cur} />
                </div>
                <p style={{ fontSize: "12px", color: "#94a3b8" }}>Total tax &middot; {taxRate}% effective</p>
              </div>
              {/* PoEM */}
              <div style={{
                padding: "24px 20px",
                background: "rgba(39,174,96,0.06)",
                border: "1px solid rgba(39,174,96,0.15)",
                borderRadius: "16px",
              }}>
                <p style={{ fontSize: "11px", letterSpacing: "1.5px", textTransform: "uppercase", color: "#27ae60", marginBottom: "16px", fontWeight: 600 }}>
                  Under UAE Structure
                </p>
                <div style={{ fontSize: "28px", fontWeight: 700, color: "#27ae60", marginBottom: "4px" }}>
                  <AnimatedNumber value={totalPoem} currency={cur} />
                </div>
                <p style={{ fontSize: "12px", color: "#94a3b8" }}>Total cost &middot; ~{Math.round((totalPoem / rev) * 100)}% effective</p>
              </div>
            </div>

            {/* Breakdown */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "16px",
              padding: "24px",
              marginBottom: "24px",
            }}>
              <p style={{ fontSize: "12px", letterSpacing: "1.5px", textTransform: "uppercase", color: "#D4A843", marginBottom: "16px", fontWeight: 600 }}>
                Cost Breakdown
              </p>
              {[
                { label: "UAE Corporate Tax (9%)", value: uaeTax, color: "#64748b" },
                { label: "Treasury Advisory Fee (8%)", value: vestonFee, color: "#64748b" },
                { label: "Administration", value: admin, color: "#64748b" },
                { label: "Total Annual Cost", value: totalPoem, color: "#D4A843", bold: true },
                { label: "Your Current Tax", value: currentTax, color: "#ef4444", bold: true },
              ].map((item, i) => (
                <div key={i} style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "10px 0",
                  borderBottom: i < 4 ? "1px solid rgba(255,255,255,0.04)" : "none",
                }}>
                  <span style={{
                    fontSize: "13px",
                    color: item.bold ? item.color : "#94a3b8",
                    fontWeight: item.bold ? 700 : 400,
                  }}>
                    {item.label}
                  </span>
                  <span style={{
                    fontSize: item.bold ? "16px" : "14px",
                    fontWeight: item.bold ? 700 : 500,
                    color: item.color,
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    {fmt(item.value, cur)}
                  </span>
                </div>
              ))}
            </div>

            {/* Key facts */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "10px",
              marginBottom: "24px",
            }}>
              {[
                { label: "Relocation", value: "Not required", icon: "\u2708\uFE0F" },
                { label: "Dubai visits", value: "24hrs / 6 months", icon: "\u{1F550}" },
                { label: "Business change", value: "None", icon: "\u{1F3E2}" },
              ].map((f, i) => (
                <div key={i} style={{
                  padding: "16px 12px",
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: "12px",
                  textAlign: "center",
                }}>
                  <div style={{ fontSize: "20px", marginBottom: "6px" }}>{f.icon}</div>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: "#e2e8f0", marginBottom: "2px" }}>{f.value}</div>
                  <div style={{ fontSize: "10px", color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>{f.label}</div>
                </div>
              ))}
            </div>

            {/* CTA */}
            {!submitted ? (
              <div style={{
                background: "rgba(212,168,67,0.06)",
                border: "1px solid rgba(212,168,67,0.2)",
                borderRadius: "16px",
                padding: "28px 24px",
                textAlign: "center",
              }}>
                <p style={{ fontSize: "16px", fontWeight: 600, color: "#D4A843", marginBottom: "4px" }}>
                  Ready to explore this structure?
                </p>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px" }}>
                  Request a free 15-minute structuring consultation
                </p>
                <div style={{ display: "flex", gap: "10px", maxWidth: "420px", margin: "0 auto" }}>
                  <input
                    type="email"
                    placeholder="Your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "12px 16px",
                      borderRadius: "10px",
                      border: "1px solid rgba(255,255,255,0.1)",
                      background: "rgba(255,255,255,0.04)",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                  />
                  <button
                    onClick={() => email.includes("@") && setSubmitted(true)}
                    style={{
                      padding: "12px 24px",
                      borderRadius: "10px",
                      border: "none",
                      background: "linear-gradient(135deg, #D4A843, #b8912e)",
                      color: "#0a0f1a",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Request Consultation
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                background: "rgba(39,174,96,0.08)",
                border: "1px solid rgba(39,174,96,0.2)",
                borderRadius: "16px",
                padding: "28px 24px",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "28px", marginBottom: "8px" }}>{"\u2713"}</div>
                <p style={{ fontSize: "16px", fontWeight: 600, color: "#27ae60", marginBottom: "4px" }}>
                  Consultation requested
                </p>
                <p style={{ fontSize: "13px", color: "#94a3b8" }}>
                  Reid will be in touch within 24 hours with a personalised structuring review.
                </p>
              </div>
            )}

            {/* Reset */}
            <div style={{ textAlign: "center", marginTop: "20px" }}>
              <button
                onClick={() => { setShowResults(false); setSubmitted(false); setEmail(""); }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#64748b",
                  fontSize: "13px",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Calculate again
              </button>
            </div>

            {/* Disclaimer */}
            <p style={{
              fontSize: "10px",
              color: "#475569",
              textAlign: "center",
              marginTop: "32px",
              lineHeight: 1.5,
              maxWidth: "500px",
              margin: "32px auto 0",
            }}>
              This calculator provides indicative estimates only. Actual savings depend on individual circumstances,
              business structure, and treaty application. Subject to professional assessment. Veston Partners provides
              international treasury and strategic finance advisory services. Past performance is not indicative of future results.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
