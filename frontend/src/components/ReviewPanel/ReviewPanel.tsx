/** Admin: очередь ручной валидации matching'а (транзакция -> здание). */
import { useCallback, useEffect, useState } from "react";
import "./ReviewPanel.css";

interface ReviewItem {
  id: number;
  entity_type: string;
  source_name: string | null;
  candidate_building_id: number | null;
  candidate_name: string | null;
  score: number | null;
}

export function ReviewPanel({ onClose }: { onClose: () => void }) {
  const [token, setToken] = useState(localStorage.getItem("admin_token") ?? "");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [authed, setAuthed] = useState(false);

  const load = useCallback(async (tok: string) => {
    setError(null);
    try {
      const resp = await fetch("/api/review", { headers: { "X-Admin-Token": tok } });
      if (!resp.ok) {
        setAuthed(false);
        setError(resp.status === 401 ? "Wrong token" : `Error ${resp.status}`);
        return;
      }
      const data = await resp.json();
      setItems(data.pending);
      setAuthed(true);
      localStorage.setItem("admin_token", tok);
    } catch {
      setError("API unavailable");
    }
  }, []);

  useEffect(() => {
    if (token) void load(token);
  }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  const resolve = async (id: number, action: "approve" | "reject") => {
    await fetch(`/api/review/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Token": token },
      body: JSON.stringify({ action }),
    });
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  return (
    <div className="info-overlay" onClick={onClose}>
      <div className="review-panel" onClick={(e) => e.stopPropagation()}>
        <div className="info-header">
          <h2>Match review queue</h2>
          <button className="card-close" onClick={onClose}>✕</button>
        </div>

        {!authed && (
          <div className="review-auth">
            <input
              type="password"
              placeholder="Admin token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
            <button onClick={() => load(token)}>Load</button>
            {error && <span className="review-error">{error}</span>}
          </div>
        )}

        {authed && (
          <>
            <p className="info-note">
              {items.length} pending. Approve = link transaction to building and
              remember the alias; reject = leave unmatched.
            </p>
            <ul className="review-list">
              {items.map((item) => (
                <li key={item.id} className="review-item">
                  <div className="review-names">
                    <span className="review-source">{item.source_name ?? "?"}</span>
                    <span className="review-arrow">→</span>
                    <span className="review-candidate">{item.candidate_name ?? "?"}</span>
                    <span className="review-score">
                      {item.score?.toFixed(0)} · {item.entity_type === "sales_transaction" ? "sale" : "rent"}
                    </span>
                  </div>
                  <div className="review-actions">
                    <button className="btn-approve" onClick={() => resolve(item.id, "approve")}>
                      ✓
                    </button>
                    <button className="btn-reject" onClick={() => resolve(item.id, "reject")}>
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
