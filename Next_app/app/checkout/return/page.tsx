
"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

function CheckoutReturnContent() {
  const params = useSearchParams();
  const orderId = params.get("token");

  const [status, setStatus] = useState<
    "loading" | "success" | "failed"
  >("loading");

  const [message, setMessage] = useState("Verifying your payment...");

  useEffect(() => {
    if (!orderId) {
      setStatus("failed");
      setMessage("Missing PayPal order ID.");
      return;
    }

    let cancelled = false;

    async function capture() {
      try {
        const res = await fetch("/api/payments/capture", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ orderId }),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || "Payment capture failed.");
        }

        if (!cancelled) {
          setStatus("success");
          setMessage("Your payment was completed successfully!");
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("failed");
          setMessage(
            err instanceof Error
              ? err.message
              : "Unable to verify payment."
          );
        }
      }
    }

    capture();

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  return (
    <main className="page">
      <section className="loading-section">
        {status === "loading" && <div className="spinner" />}

        {status === "success" && (
          <div style={{ fontSize: 42 }}>✓</div>
        )}

        {status === "failed" && (
          <div style={{ fontSize: 42 }}>!</div>
        )}

        <h2>
          {status === "loading"
            ? "Processing order"
            : status === "success"
              ? "Payment successful"
              : "Payment unsuccessful"}
        </h2>

        <p>{message}</p>

        {status !== "loading" && (
          <button
            className="primary"
            onClick={() => (window.location.href = "/")}
          >
            Back to GhostBuyer
          </button>
        )}
      </section>
    </main>
  );
}

export default function CheckoutReturnPage() {
  return (
    <Suspense fallback={<div className="loading-section"><div className="spinner" /></div>}>
      <CheckoutReturnContent />
    </Suspense>
  );
}
