import json
import os
import re
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "gemini_configured": bool(GEMINI_API_KEY),
                    "message": "Set GEMINI_API_KEY in Render environment variables." if not GEMINI_API_KEY else "Gemini key is configured."})

@app.post("/api/research")
def research():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key is not configured. In Render, add GEMINI_API_KEY under Environment, then redeploy."}), 503
    data = request.get_json(silent=True) or {}
    niche = str(data.get("niche", "")).strip()[:180]
    customer = str(data.get("customer", "")).strip()[:180]
    country = str(data.get("country", "")).strip()[:80]
    state = str(data.get("state", "")).strip()[:100]
    city = str(data.get("city", "")).strip()[:100]
    focus = str(data.get("focus", "any")).strip()[:120]
    notes = str(data.get("notes", "")).strip()[:1000]
    if len(niche) < 2 or len(customer) < 2:
        return jsonify({"error": "Please provide a niche and target customer."}), 400
    market = ", ".join(x for x in [city, state, country] if x) or "not specified"
    prompt = f'''You are ProductPilot AI, a practical ecommerce product research assistant. Analyze this business opportunity:
Niche: {niche}
Target customer: {customer}
Market: {market}
Focus: {focus}
Additional notes: {notes or 'None'}
Return ONLY valid JSON, no markdown, matching this schema:
{{"problem":"1-3 sentence summary of the customer problem","products":[{{"name":"specific product idea","why":"why it solves a customer pain point and why it may fit this market","demand":0,"competition":"Low|Medium|High","risk":"Low|Medium|High","opportunity":"High|Medium|Low","usd":[20,40],"risks":["risk 1","risk 2","risk 3"],"next":["validation step 1","step 2","step 3"],"metrics":["Estimated gross margin: 25-40%","Demand signal: hypothesis to validate"]}}]}}
Provide exactly 3 distinct products. demand must be an integer from 0 to 100. usd must contain two numeric price estimates in USD, low then high. Use cautious estimates and clearly treat market numbers as hypotheses, not verified live data. Do not claim you searched current marketplaces or reviewed real customer data. Keep each string concise.'''
    body = {
        "system_instruction": {"parts": [{"text": "You generate structured, cautious product research. Never invent that estimates are verified facts. Output JSON only."}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "responseMimeType": "application/json"}
    }
    try:
        resp = requests.post(GEMINI_URL, headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}, json=body, timeout=60)
        if resp.status_code >= 400:
            detail = "Gemini API request failed. Check API key, model name and quota."
            try:
                msg = resp.json().get("error", {}).get("message", "")
                if msg:
                    detail = msg[:500]
            except Exception:
                pass
            return jsonify({"error": detail}), 502
        result = resp.json()
        text = "".join(part.get("text", "") for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        # Defensive handling if a model returns fenced JSON despite JSON mode.
        text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.I)
        parsed = json.loads(text)
        products = parsed.get("products", [])
        if not isinstance(products, list) or not products:
            raise ValueError("Gemini returned no product ideas")
        clean = []
        for p in products[:3]:
            if not isinstance(p, dict):
                continue
            usd = p.get("usd", [20, 40])
            if not isinstance(usd, list) or len(usd) < 2:
                usd = [20, 40]
            try:
                low, high = sorted([max(1, min(100000, float(usd[0]))), max(1, min(100000, float(usd[1])))])
            except (TypeError, ValueError):
                low, high = 20, 40
            try:
                demand = max(0, min(100, int(float(p.get("demand", 65)))))
            except (TypeError, ValueError):
                demand = 65
            def short_list(v, limit=3):
                if not isinstance(v, list): return []
                return [str(x)[:220] for x in v[:limit]]
            clean.append({
                "name": str(p.get("name", "Product opportunity"))[:140],
                "why": str(p.get("why", p.get("description", "Potential product opportunity")))[:600],
                "demand": demand,
                "competition": p.get("competition") if p.get("competition") in ["Low", "Medium", "High"] else "Medium",
                "risk": p.get("risk") if p.get("risk") in ["Low", "Medium", "High"] else "Medium",
                "opportunity": p.get("opportunity") if p.get("opportunity") in ["Low", "Medium", "High"] else "Medium",
                "usd": [round(low, 2), round(high, 2)],
                "risks": short_list(p.get("risks")),
                "next": short_list(p.get("next")),
                "metrics": short_list(p.get("metrics"), 4)
            })
        if not clean:
            raise ValueError("Gemini response had no usable product ideas")
        return jsonify({"problem": str(parsed.get("problem", "Potential customer problem identified."))[:1000], "products": clean})
    except requests.Timeout:
        return jsonify({"error": "Gemini took too long to respond. Please retry."}), 504
    except requests.RequestException:
        return jsonify({"error": "Could not connect to Gemini. Check server logs and try again."}), 502
    except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return jsonify({"error": "Gemini returned an unreadable report. Please retry."}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
