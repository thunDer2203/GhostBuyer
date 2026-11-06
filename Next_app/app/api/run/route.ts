import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { query, auto_pay } = await req.json();
    if (typeof query !== "string" || !query.trim() || query.length > 200) {
      return NextResponse.json({ error: "Enter what you want to buy (max 200 characters)." }, { status: 400 });
    }


    const response = await fetch(`${process.env.AI_BASE_URL}/ai/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query.trim(),
        auto_pay: auto_pay || false,
      }),
    });
    console.log(response);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "AI Recommender server responded with an error");
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err: any) {
    console.error("run crashed:", err);
    return NextResponse.json({ error: err.message || "Server error" }, { status: 500 });
  }
}