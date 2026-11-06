"use client";

import { useState } from "react";

export default function MerchantDashboard() {
  return (
    <>
      <nav className="nav">
        <div className="brand">
          <span className="logo">G</span>
          <strong>GhostBuyer</strong>
        </div>
        <span className="pill">Merchant Dashboard</span>
      </nav>

      <main className="page">
        <section className="hero">
          <h1>Welcome, Merchant</h1>
          <p>
            Your store is almost ready. Please complete the verification process
            to allow GhostBuyer agents to start listing your products.
          </p>
        </section>

        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          <section className="card">
            <h2>DNS Verification</h2>
            <p className="muted">
              Verify that you own the domain associated with your store.
              This is the first step to becoming a trusted seller.
            </p>
            <button className="primary wide" onClick={() => alert("Starting DNS Verification process...")}>
              Start DNS Verification
            </button>
          </section>

          <section className="card">
            <h2>Email Verification</h2>
            <p className="muted">
              Verify your contact email address to ensure you receive
              important order notifications and payment updates.
            </p>
            <button className="primary wide" onClick={() => alert("Starting Email Verification process...")}>
              Start Email Verification
            </button>
          </section>
        </div>

        <section className="card" style={{ marginTop: "24px" }}>
          <h2>Store Status</h2>
          <div className="row">
            <span className="muted">Account Status</span>
            <span className="status review">Pending Verification</span>
          </div>
          <div className="row">
            <span className="muted">DNS Status</span>
            <span className="status block">Not Started</span>
          </div>
          <div className="row">
            <span className="muted">Email Status</span>
            <span className="status block">Not Started</span>
          </div>
        </section>
      </main>
    </>
  );
}
