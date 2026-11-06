"use client";

import { useState } from "react";

export default function MerchantOnboarding() {
  const [formData, setFormData] = useState({
    email: "",
    name: "",
    productTypes: "",
    catalogApi: "",
    orderApi: "",
  });
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Basic validation
    if (Object.values(formData).some((val) => !val.trim())) {
      alert("Please fill in all fields.");
      return;
    }

    console.log("Merchant Onboarding Submission:", formData);
    setSubmitted(true);
  };

  return (
    <>
      <nav className="nav">
        <div className="brand">
          <span className="logo">G</span>
          <strong>GhostBuyer</strong>
        </div>
        <span className="pill">Merchant Portal</span>
      </nav>

      <main className="page">
        <section className="hero">
          <h1>
            Join the network.
            <br />
            Reach more buyers.
          </h1>
          <p>
            Register your store and connect your API endpoints to allow GhostBuyer
            agents to find and purchase your products securely.
          </p>
        </section>

        {!submitted ? (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "600px", margin: "0 auto", width: "100%" }}>
            <section className="card">
              <h2>Identity</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label className="muted">Merchant Email</label>
                  <input
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="merchant@store.com"
                    style={{ padding: "10px", border: "1px solid var(--line)", borderRadius: "8px", font: "inherit" }}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label className="muted">Merchant/Store Name</label>
                  <input
                    name="name"
                    type="text"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="e.g. TechGadgets Inc."
                    style={{ padding: "10px", border: "1px solid var(--line)", borderRadius: "8px", font: "inherit" }}
                  />
                </div>
              </div>
            </section>

            <section className="card">
              <h2>Business Details</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label className="muted">Type of products you sell</label>
                <textarea
                  name="productTypes"
                  value={formData.productTypes}
                  onChange={handleChange}
                  placeholder="e.g. High-end electronics, noise-cancelling headphones, mechanical keyboards..."
                  style={{ padding: "10px", border: "1px solid var(--line)", borderRadius: "8px", font: "inherit", minHeight: "80px", resize: "vertical" }}
                />
              </div>
            </section>

            <section className="card">
              <h2>API Integration</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label className="muted">Product Catalog API</label>
                  <input
                    name="catalogApi"
                    type="url"
                    value={formData.catalogApi}
                    onChange={handleChange}
                    placeholder="https://api.yourstore.com/v1/products"
                    style={{ padding: "10px", border: "1px solid var(--line)", borderRadius: "8px", font: "inherit" }}
                  />
                  <span className="muted" style={{ fontSize: "12px" }}>Endpoint for GhostBuyer to fetch catalog and quantity.</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label className="muted">Order Creation API</label>
                  <input
                    name="orderApi"
                    type="url"
                    value={formData.orderApi}
                    onChange={handleChange}
                    placeholder="https://api.yourstore.com/v1/orders"
                    style={{ padding: "10px", border: "1px solid var(--line)", borderRadius: "8px", font: "inherit" }}
                  />
                  <span className="muted" style={{ fontSize: "12px" }}>Endpoint for GhostBuyer to place approved orders.</span>
                </div>
              </div>
            </section>

            <button type="submit" className="primary wide">
              Complete Onboarding
            </button>
          </form>
        ) : (
          <div className="card" style={{ maxWidth: "600px", margin: "0 auto", textAlign: "center" }}>
            <div className="success">
              <strong>Registration Successful!</strong>
              <p style={{ margin: "8px 0 0" }}>Your merchant account has been created. Our agents can now start exploring your catalog.</p>
            </div>
            <button
              className="primary wide"
              onClick={() => setSubmitted(false)}
              style={{ marginTop: "20px" }}
            >
              Edit Details
            </button>
          </div>
        )}
      </main>
    </>
  );
}
