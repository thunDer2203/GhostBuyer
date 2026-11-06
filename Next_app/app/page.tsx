
"use client";

import { useEffect, useState } from "react";
import { PayPalButtons, PayPalScriptProvider } from "@paypal/react-paypal-js";

type Recommendation = {
  status: string | null;
  productId: string;
  title: string;
  price: number;
  rankingReasons: string[];
  paypal_order_id: string | null;
  approval_url: string | null;
  message?: string;
};

type PaymentState = "idle" | "processing" | "success" | "failed";

const SUGGESTIONS = [
  "Best headphones under ₹5,000",
  "Smartwatch under ₹3,000",
  "Laptop bag under ₹1,500",
];

const REVEAL_DURATION = 10;

const usd = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);

function getApprovalUrl(value: string | null) {
  if (!value) return null;

  try {
    const url = new URL(value);

    if (
      url.protocol !== "https:" ||
      !(
        url.hostname === "paypal.com" ||
        url.hostname.endsWith(".paypal.com")
      )
    ) {
      return null;
    }

    return url.toString();
  } catch {
    return null;
  }
}

export default function Home() {
  const [query, setQuery] = useState(SUGGESTIONS[0]);
  const [autoPay, setAutoPay] = useState(false);
  const [loading, setLoading] = useState(false);

  const [products, setProducts] = useState<Recommendation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [payment, setPayment] = useState<PaymentState>("idle");
  const [error, setError] = useState("");

  // Product reveal state
  const [autoCheckout, setAutoCheckout] =
    useState<Recommendation | null>(null);

  const [countdown, setCountdown] = useState(REVEAL_DURATION);

  const selected =
    products.find((p) => p.productId === selectedId) ?? null;

  // Automatic PayPal redirect countdown
  useEffect(() => {
    if (!autoCheckout?.approval_url) return;

    if (countdown <= 0) {
      window.location.assign(autoCheckout.approval_url);
      return;
    }

    const timer = setTimeout(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [autoCheckout, countdown]);

  function continueToPayPal() {
    if (!autoCheckout?.approval_url) return;

    window.location.assign(autoCheckout.approval_url);
  }

  function cancelReveal() {
    setAutoCheckout(null);
    setCountdown(REVEAL_DURATION);
  }

  async function startRun() {
    if (!query.trim() || loading) return;

    setLoading(true);
    setProducts([]);
    setSelectedId(null);
    setPayment("idle");
    setError("");

    setAutoCheckout(null);
    setCountdown(REVEAL_DURATION);

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query.trim(),
          auto_pay: autoPay,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Unable to complete your request.");
      }

      const recommendations: Recommendation[] = Array.isArray(data)
        ? data
        : data
          ? [data]
          : [];

      if (recommendations.length === 0) {
        throw new Error("No matching products found.");
      }

      // AUTO PAY: Show product reveal before PayPal redirect.
      if (autoPay) {
        const result = recommendations[0];

        if (result.status === "payment_failed") {
          throw new Error(
            result.message || "Unable to create PayPal order."
          );
        }

        const approvalUrl = getApprovalUrl(result.approval_url);

        if (!result.paypal_order_id || !approvalUrl) {
          throw new Error(
            "PayPal order was not created successfully. Please try again."
          );
        }

        // Store selected product and show reveal screen.
        setAutoCheckout({
          ...result,
          approval_url: approvalUrl,
        });

        setCountdown(REVEAL_DURATION);

        return;
      }

      // MANUAL MODE: Display all ranked products.
      setProducts(recommendations);
      setSelectedId(recommendations[0].productId);

    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  async function capturePayment(orderId: string) {
    setPayment("processing");

    try {
      const res = await fetch("/api/payments/capture", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          orderId,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Payment capture failed.");
      }

      setPayment("success");
    } catch (err) {
      console.error(err);
      setPayment("failed");
    }
  }

  return (
    <PayPalScriptProvider
      options={{
        clientId: process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID!,
        currency: "USD",
        intent: "capture",
      }}
    >
      <nav className="nav">
        <div className="brand">
          <span className="logo">G</span>
          <strong>GhostBuyer</strong>
        </div>

        <span className="pill">PayPal Sandbox</span>
      </nav>

      <main className="page">

        {/* PRODUCT REVEAL SCREEN */}
        {autoCheckout ? (
          <section
            className="loading-section"
            style={{
              maxWidth: 650,
              margin: "50px auto",
              padding: "32px",
              textAlign: "center",
              background: "var(--card, #fff)",
              borderRadius: 20,
              border: "1px solid var(--border, #e5e7eb)",
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: 2,
                color: "#16a34a",
                marginBottom: 12,
              }}
            >
              GHOSTBUYER AI RECOMMENDATION
            </div>

            <h1 style={{ marginBottom: 8 }}>
              We found your match!
            </h1>

            <p className="muted">
              Based on your requirements, our AI agents selected
              this product for you.
            </p>

            {/* Product information */}
            <div
              style={{
                margin: "28px 0",
                padding: 24,
                borderRadius: 16,
                background: "var(--background, #f8fafc)",
                textAlign: "left",
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#16a34a",
                  marginBottom: 10,
                }}
              >
                BEST MATCH FOR YOUR QUERY
              </div>

              <h2 style={{ fontSize: 24, marginBottom: 12 }}>
                {autoCheckout.title}
              </h2>

              <div
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  marginBottom: 20,
                }}
              >
                {usd(autoCheckout.price)}
              </div>

              <div
                style={{
                  borderTop: "1px solid var(--border, #e5e7eb)",
                  paddingTop: 16,
                }}
              >
                <strong>Why GhostBuyer selected this</strong>

                <ul
                  style={{
                    paddingLeft: 20,
                    marginTop: 12,
                    lineHeight: 1.8,
                  }}
                >
                  {autoCheckout.rankingReasons?.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Countdown */}
            <div style={{ marginBottom: 24 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 12,
                }}
              >
                <strong>Redirecting to PayPal...</strong>

                <span
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: "#16a34a",
                  }}
                >
                  {countdown}s
                </span>
              </div>

              <div
                style={{
                  height: 8,
                  background: "#e5e7eb",
                  borderRadius: 20,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${
                      ((REVEAL_DURATION - countdown) /
                        REVEAL_DURATION) *
                      100
                    }%`,
                    background: "#16a34a",
                    borderRadius: 20,
                    transition: "width 1s linear",
                  }}
                />
              </div>

              <p className="muted" style={{ marginTop: 12 }}>
                Review your selected product before proceeding
                to payment.
              </p>
            </div>

            {/* Actions */}
            <button
              className="primary"
              onClick={continueToPayPal}
              style={{
                width: "100%",
                padding: 16,
                fontSize: 16,
              }}
            >
              Continue to PayPal →
            </button>

            <button
              onClick={cancelReveal}
              style={{
                marginTop: 16,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "var(--muted-foreground, #64748b)",
                fontSize: 14,
              }}
            >
              Back to GhostBuyer
            </button>
          </section>
        ) : (
          <>
            {/* HERO */}
            <section className="hero">
              <h1>
                Your AI. Your budget.
                <br />
                Your control.
              </h1>

              <p>
                Tell GhostBuyer what you need. AI agents find products,
                evaluate sellers and screen for fraud.
                Nothing is paid until you approve.
              </p>

              <div className="command">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Describe what to buy and your budget"
                  aria-label="What do you want to buy?"
                  disabled={loading}
                />

                <div
                  className="autopay-toggle"
                  onClick={() => !loading && setAutoPay(!autoPay)}
                  role="switch"
                  aria-checked={autoPay}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      if (!loading) setAutoPay(!autoPay);
                    }
                  }}
                >
                  <div className={`switch ${autoPay ? "on" : ""}`}>
                    <span />
                  </div>
                  <span>Auto Pay</span>
                </div>

                <button
                  className="primary"
                  onClick={startRun}
                  disabled={loading || !query.trim()}
                >
                  {loading ? "Searching..." : "Find products"}
                </button>
              </div>

              <div className="chips">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="chip"
                    onClick={() => setQuery(s)}
                    disabled={loading}
                  >
                    {s}
                  </button>
                ))}
              </div>

              <ul className="trust">
                <li>Spending limit you set</li>
                <li>Every seller checked for fraud</li>
                <li>You approve every payment</li>
              </ul>
            </section>

            {/* LOADING */}
            {loading && (
              <section className="loading-section">
                <div className="spinner" />
                <h3>GhostBuyer is working...</h3>
                <p>
                  Searching products, checking merchant trust
                  and evaluating the best match.
                </p>
              </section>
            )}

            {/* ERRORS */}
            {error && (
              <div className="error-box">
                <strong>Something went wrong</strong>
                <p>{error}</p>
                <button onClick={() => setError("")}>Dismiss</button>
              </div>
            )}

            {/* MANUAL MODE RESULTS */}
            {!loading && products.length > 0 && (
              <div className="grid">
                <section>
                  <h2>Recommended products</h2>

                  <p className="muted">
                    Products ranked by semantic similarity and product quality.
                  </p>

                  <div className="products">
                    {products.map((p, index) => (
                      <label
                        key={p.productId}
                        className={`product ${
                          p.productId === selectedId ? "selected" : ""
                        }`}
                      >
                        <input
                          type="radio"
                          name="product"
                          checked={p.productId === selectedId}
                          onChange={() => {
                            setSelectedId(p.productId);
                            setPayment("idle");
                          }}
                        />

                        <div className="p-main">
                          <div className="p-head">
                            <div>
                              <span className="muted">
                                Recommendation #{index + 1}
                              </span>

                              <strong>{p.title}</strong>

                              <div className="muted">
                                Product ID: {p.productId}
                              </div>
                            </div>

                            <div className="p-price">
                              <strong>{usd(p.price)}</strong>
                            </div>
                          </div>

                          <div className="ranking-reasons">
                            <strong>Why this product?</strong>

                            <ul>
                              {p.rankingReasons?.map((reason, i) => (
                                <li key={i}>{reason}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </section>

                {/* CHECKOUT */}
                <aside>
                  <section className="card">
                    <h2>Checkout</h2>

                    {selected ? (
                      <>
                        <div className="row">
                          <span className="muted">Item</span>
                          <strong>{selected.title}</strong>
                        </div>

                        <div className="row">
                          <span className="muted">Total</span>
                          <strong>{usd(selected.price)}</strong>
                        </div>

                        {payment === "success" ? (
                          <p className="success">
                            Payment completed successfully!
                          </p>
                        ) : (
                          <div style={{ marginTop: 16 }}>
                            <PayPalButtons
                              key={selected.productId}
                              style={{
                                layout: "vertical",
                                shape: "rect",
                                label: "pay",
                              }}
                              disabled={payment === "processing"}
                              createOrder={async () => {
                                const res = await fetch(
                                  "/api/payments/create-order",
                                  {
                                    method: "POST",
                                    headers: {
                                      "Content-Type": "application/json",
                                    },
                                    body: JSON.stringify({
                                      productId: selected.productId,
                                      requestId: crypto.randomUUID(),
                                    }),
                                  }
                                );

                                const data = await res.json();

                                if (!res.ok) {
                                  throw new Error(data.error);
                                }

                                return data.orderId;
                              }}
                              onApprove={async (data) => {
                                await capturePayment(data.orderID);
                              }}
                              onError={(err) => {
                                console.error("PayPal error:", err);
                                setPayment("failed");
                              }}
                            />
                          </div>
                        )}

                        {payment === "processing" && (
                          <p className="muted">
                            Processing payment...
                          </p>
                        )}

                        {payment === "failed" && (
                          <p className="error">
                            Payment failed. Please try again.
                          </p>
                        )}

                        <p className="note">
                          Nothing is charged until you approve.
                        </p>
                      </>
                    ) : (
                      <p className="muted">
                        Select a product to continue.
                      </p>
                    )}
                  </section>
                </aside>
              </div>
            )}
          </>
        )}
      </main>
    </PayPalScriptProvider>
  );
}
