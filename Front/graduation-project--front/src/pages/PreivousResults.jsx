import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/MainTest.css";
import "../styles/PreviousResults.css";

import { API_URL } from "../config";

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-EG", {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function PreviousResults() {
  const navigate = useNavigate();
  const email    = localStorage.getItem("userEmail") || "";

  const [results,  setResults]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!email) { setLoading(false); return; }

    fetch(`${API_URL}/quiz/results?email=${encodeURIComponent(email)}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        setResults(data.results || []);
      })
      .catch(e => setError(e.message || "Failed to load results."))
      .finally(() => setLoading(false));
  }, [email]);

  const toggle = (idx) => setExpanded(prev => prev === idx ? null : idx);

  // ── Not logged in ─────────────────────────────────────────
  if (!email) return (
    <div className="ep-page">
      <PageHeader />
      <main className="ep-main">
        <div className="ep-card pr-empty-card">
          <div className="pr-empty-icon">🔒</div>
          <h3>Sign in to see your results</h3>
          <p>Your quiz results are saved to your account. Log in to access them.</p>
          <button className="ep-btn ep-btn-primary" onClick={() => navigate("/login")}>
            Go to Login
          </button>
        </div>
      </main>
    </div>
  );

  // ── Loading ───────────────────────────────────────────────
  if (loading) return (
    <div className="ep-page">
      <PageHeader />
      <main className="ep-main">
        <div className="ep-card pr-empty-card">
          <span className="ep-spinner pr-spinner" />
          <p>Loading your results…</p>
        </div>
      </main>
    </div>
  );

  // ── Error ─────────────────────────────────────────────────
  if (error) return (
    <div className="ep-page">
      <PageHeader />
      <main className="ep-main">
        <div className="ep-card pr-empty-card">
          <div className="pr-empty-icon">⚠️</div>
          <p className="ep-error">{error}</p>
          <button className="ep-btn ep-btn-primary" onClick={() => navigate("/test/main-test")}>
            Take the Quiz
          </button>
        </div>
      </main>
    </div>
  );

  // ── No results yet ────────────────────────────────────────
  if (!results.length) return (
    <div className="ep-page">
      <PageHeader />
      <main className="ep-main">
        <div className="ep-card pr-empty-card">
          <div className="pr-empty-icon">📋</div>
          <h3>No results yet</h3>
          <p>Complete the career quiz to see your personalized analysis here.</p>
          <button className="ep-btn ep-btn-primary" onClick={() => navigate("/test/main-test")}>
            Take the Quiz
          </button>
        </div>
      </main>
    </div>
  );

  // ── Results list ──────────────────────────────────────────
  return (
    <div className="ep-page">
      <PageHeader />
      <main className="pr-main">
        <div className="pr-container">

          <div className="pr-page-title">
            <h2>Your Quiz History</h2>
            <p>{results.length} result{results.length !== 1 ? "s" : ""} found</p>
          </div>

          <div className="pr-list">
            {results.map((item, idx) => {
              const r   = item.result || {};
              const top = r.top_track  || "—";
              const pct = r.match_pct  ?? 0;
              const scores = r.scores?.filter(s => s.pct > 0) || [];
              const isOpen = expanded === idx;

              return (
                <div key={idx} className={`pr-card${isOpen ? " pr-card--open" : ""}`}>
                  {/* Card header */}
                  <button className="pr-card-header" onClick={() => toggle(idx)}>
                    <div className="pr-card-left">
                      <span className="pr-card-emoji">{r.top_emoji || "🎯"}</span>
                      <div>
                        <span className="pr-card-track">{top}</span>
                        <span className="pr-card-date">{formatDate(item.submitted_at)}</span>
                        {scores.length > 1 && (
                          <span className="pr-top-chips">
                            {scores.slice(0, 3).map(s => (
                              <span key={s.key} className="pr-top-chip">
                                {s.emoji} {s.track} {s.pct}%
                              </span>
                            ))}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="pr-card-right">
                      <div className="pr-mini-bar-wrap">
                        <div className="pr-mini-bar" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="pr-card-pct">{pct}%</span>
                      <span className="pr-chevron">{isOpen ? "▲" : "▼"}</span>
                    </div>
                  </button>

                  {/* Expanded details */}
                  {isOpen && (
                    <div className="pr-card-body">
                      {r.insight && (
                        <p className="pr-insight">{r.insight}</p>
                      )}

                      {scores.length > 0 && (
                        <div className="ep-scores pr-scores">
                          <p className="ep-scores-title">Profile Breakdown</p>
                          {scores.map(s => (
                            <div key={s.key} className="ep-score-row">
                              <span className="ep-score-label">{s.emoji} {s.track}</span>
                              <div className="ep-score-bar-wrap">
                                <div
                                  className={`ep-score-bar${s.key === r.top_key ? " ep-score-bar--top" : ""}`}
                                  style={{ width: `${s.pct}%` }}
                                />
                              </div>
                              <span className="ep-score-pct">{s.pct}%</span>
                            </div>
                          ))}
                        </div>
                      )}

                      <button
                        className="ep-btn ep-btn-primary pr-roadmap-btn"
                        onClick={() => navigate("/roadmap", { state: { suggestedTrack: top } })}
                      >
                        Build {top} Roadmap →
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="pr-footer">
            <button className="ep-btn ep-btn-primary" onClick={() => navigate("/test/main-test")}>
              Take Quiz Again
            </button>
          </div>

        </div>
      </main>
    </div>
  );
}

function PageHeader() {
  const navigate = useNavigate();
  return (
    <header className="ep-header">
      <div className="ep-logo" style={{ cursor: "pointer" }} onClick={() => navigate("/test")}>
        EduPick
      </div>
      <span className="ep-tagline">Previous Results</span>
    </header>
  );
}
