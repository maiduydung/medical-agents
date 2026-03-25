// ============================================
// MEDICAL AGENT — FigJam Diagram Builder
// Paste this into: Plugins → Development → Open Console → paste → Run
// ============================================

(async () => {
  const page = figma.currentPage;
  const med = page.findOne(n => n.name === "Medical Agent" && n.type === "SECTION");

  if (!med) {
    figma.notify("❌ Could not find 'Medical Agent' section");
    return;
  }

  // Clear existing children
  while (med.children.length > 0) med.children[0].remove();
  figma.notify("🏗️ Building Medical Agent diagram...");

  // ---- Colors ----
  const LBLUE   = { r: 0.85, g: 0.92, b: 1.0 };
  const LGREEN  = { r: 0.84, g: 0.96, b: 0.88 };
  const LORANGE = { r: 1.0,  g: 0.93, b: 0.82 };
  const LRED    = { r: 1.0,  g: 0.88, b: 0.88 };
  const LPURPLE = { r: 0.93, g: 0.88, b: 1.0 };
  const LYELLOW = { r: 1.0,  g: 0.96, b: 0.82 };
  const LGRAY   = { r: 0.94, g: 0.94, b: 0.94 };
  const LTEAL   = { r: 0.82, g: 0.96, b: 0.95 };

  // Section fill colors
  const SEC_WHITE  = { r: 1.0, g: 1.0, b: 1.0 };
  const SEC_BLUE   = { r: 0.95, g: 0.97, b: 1.0 };
  const SEC_GREEN  = { r: 0.95, g: 0.98, b: 0.96 };
  const SEC_ORANGE = { r: 0.99, g: 0.97, b: 0.94 };
  const SEC_PURPLE = { r: 0.97, g: 0.95, b: 1.0 };

  // ---- Helpers ----
  async function mkShape(parent, text, x, y, w, h, color, shapeType) {
    const s = figma.createShapeWithText();
    s.shapeType = shapeType || "ROUNDED_RECTANGLE";
    await figma.loadFontAsync(s.text.fontName);
    s.text.characters = text;
    s.x = x;
    s.y = y;
    s.resize(w, h);
    s.fills = [{ type: "SOLID", color: color }];
    parent.appendChild(s);
    return s;
  }

  function mkSection(parent, name, x, y, w, h, color) {
    const s = figma.createSection();
    s.name = name;
    s.x = x;
    s.y = y;
    s.resizeWithoutConstraints(w, h);
    if (color) s.fills = [{ type: "SOLID", color: color }];
    parent.appendChild(s);
    return s;
  }

  function mkArrow(from, to) {
    const c = figma.createConnector();
    c.connectorStart = { endpointNodeId: from.id, magnet: "AUTO" };
    c.connectorEnd   = { endpointNodeId: to.id,   magnet: "AUTO" };
    c.connectorLineType = "ELBOWED";
    c.strokeWeight = 2;
    c.strokes = [{ type: "SOLID", color: { r: 0.4, g: 0.4, b: 0.4 } }];
    c.connectorEndStrokeCap = "ARROW_LINES";
    return c;
  }

  async function mkText(parent, text, x, y, size) {
    const t = figma.createText();
    await figma.loadFontAsync({ family: "Inter", style: "Bold" });
    t.fontName = { family: "Inter", style: "Bold" };
    t.characters = text;
    t.fontSize = size || 24;
    t.x = x;
    t.y = y;
    parent.appendChild(t);
    return t;
  }

  // ======================================================
  // LAYER 1: DATA INGESTION (Event-Driven)
  // ======================================================
  const ingestionSec = mkSection(med, "Data Ingestion (Event-Driven)", 100, 100, 7800, 1000, SEC_GREEN);

  const ring = await mkShape(ingestionSec,
    "🫀 Smart Ring\n(Vitals Simulator)\n\nHR, BP, SpO2, Temp, RR\nJSON every 1 second",
    200, 200, 800, 300, LGREEN);

  const sbus = await mkShape(ingestionSec,
    "Azure Service Bus\n(vitals queue)\n\nBasic Tier ~$0.05/mo\nDecoupled ingestion",
    1600, 200, 800, 300, LBLUE, "ENG_QUEUE");

  const consumerShape = await mkShape(ingestionSec,
    "Consumer\n(Dequeue + Process)\n\nconsumer.py",
    3000, 200, 800, 300, LBLUE);

  const producerShape = await mkShape(ingestionSec,
    "producer.py\n--count 20 --interval 1\n--anomaly-chance 0.3",
    200, 600, 800, 200, LGRAY);

  const consumerPy = await mkShape(ingestionSec,
    "consumer.py\ncontinuous loop / --once",
    3000, 600, 800, 200, LGRAY);

  mkArrow(ring, sbus);
  mkArrow(sbus, consumerShape);

  // ======================================================
  // LAYER 2: FASTAPI SERVER + AGENT PIPELINE
  // ======================================================
  const fastapiSec = mkSection(med, "FastAPI Server (app/main.py)", 100, 1300, 7800, 5000, SEC_BLUE);

  const endpoint = await mkShape(fastapiSec,
    "POST /process/stream\n(SSE Streaming)\n\nStreams agent logs in real-time",
    2800, 100, 900, 250, LBLUE);

  mkArrow(consumerShape, endpoint);

  // ---- Triage Engine ----
  const triageSec = mkSection(fastapiSec, "Deterministic Triage Engine (app/tools/triage.py)", 300, 500, 7000, 700, SEC_ORANGE);

  const triage = await mkShape(triageSec,
    "⚡ Rule-Based Triage\n\nVITAL_RULES clinical thresholds\nClassifies each vital: NORMAL | WARNING | CRITICAL | EMERGENCY\nNo LLM — sub-millisecond — $0 cost",
    1200, 150, 1800, 350, LYELLOW);

  mkArrow(endpoint, triage);

  // ---- Decision Point ----
  const decision = await mkShape(fastapiSec,
    "Anomaly\nDetected?",
    3100, 1400, 500, 350, LORANGE, "DIAMOND");

  const skipAgent = await mkShape(fastapiSec,
    "✅ NORMAL\nSkip Agent — $0\nStore to Parquet only",
    600, 1450, 800, 250, LGREEN);

  const router = await mkShape(fastapiSec,
    "🔀 Supervisor Router\n(deterministic routing)\n\napp/supervisor.py\nReads triage flags → picks agent",
    4600, 1450, 900, 250, LORANGE);

  mkArrow(triage, decision);
  mkArrow(decision, skipAgent);
  mkArrow(decision, router);

  // ---- Specialist Agents ----
  const agentsSec = mkSection(fastapiSec, "Specialist Agents — LangGraph State Machines (app/agents/)", 300, 1950, 7000, 1000, SEC_WHITE);

  const cardiac = await mkShape(agentsSec,
    "❤️ Cardiac Agent\n\ncardiac.py\nTachycardia, bradycardia\narrhythmia analysis",
    200, 200, 900, 450, LRED);

  const respiratory = await mkShape(agentsSec,
    "🫁 Respiratory Agent\n\nrespiratory.py\nSpO2 drops, breathing\nrate anomalies",
    1400, 200, 900, 450, LTEAL);

  const general = await mkShape(agentsSec,
    "🩺 General Health Agent\n\ngeneral_health.py\nTemperature, BP\nmulti-metric patterns",
    2600, 200, 900, 450, LPURPLE);

  const skills = await mkShape(agentsSec,
    "📋 skills.md\n\nTool governance manifest\nDefines which agent\ngets which tools\nEnforces least-privilege",
    3900, 200, 900, 450, LYELLOW);

  mkArrow(router, cardiac);
  mkArrow(router, respiratory);
  mkArrow(router, general);

  // ---- Agent Tools ----
  const toolsSec = mkSection(fastapiSec, "Agent Tools — skills.md Governed (app/tools/)", 300, 3200, 7000, 1000, SEC_PURPLE);

  const rag = await mkShape(toolsSec,
    "📚 retrieve_docs\n\nChroma Cloud Vector Search\nFree & fast — try first\nrag_tools.py",
    200, 200, 800, 500, LPURPLE);

  const fda = await mkShape(toolsSec,
    "🏛️ openFDA API\n\nAdverse Events (MAUDE)\nDevice Recalls\nFree — no key needed\nfda_tools.py",
    1250, 200, 800, 500, LRED);

  const tavily = await mkShape(toolsSec,
    "🔍 Tavily Web Search\n\nClinical guidelines\nMedical news\nAuto-ingest to KB\nresearch_tools.py",
    2300, 200, 800, 500, LGREEN);

  const drugTool = await mkShape(toolsSec,
    "💊 FDA Drug\nInteractions\n\nSide effects check\nDrug adverse events\nfda_tools.py",
    3350, 200, 800, 500, LORANGE);

  // Connect agents → tools
  mkArrow(cardiac, rag);
  mkArrow(cardiac, fda);
  mkArrow(cardiac, tavily);
  mkArrow(respiratory, rag);
  mkArrow(respiratory, fda);
  mkArrow(respiratory, tavily);
  mkArrow(general, rag);
  mkArrow(general, drugTool);
  mkArrow(general, tavily);

  // ======================================================
  // LAYER 3: STORAGE
  // ======================================================
  const storageSec = mkSection(med, "Storage Layer", 100, 6500, 7800, 700, SEC_PURPLE);

  const parquet = await mkShape(storageSec,
    "💾 Parquet + DuckDB\n\ndata/vitals_history.parquet\nColumnar analytics — SQL queries\napp/storage.py",
    500, 150, 1000, 350, LPURPLE, "ENG_DATABASE");

  const chromaStore = await mkShape(storageSec,
    "🧠 Chroma Cloud\n\nmedical_docs collection\nSelf-improving RAG\nAuto-ingest from web search\napp/enrichment.py",
    2200, 150, 1000, 350, LBLUE, "ENG_DATABASE");

  // Connect pipeline → storage
  mkArrow(skipAgent, parquet);
  mkArrow(cardiac, parquet);
  mkArrow(respiratory, parquet);
  mkArrow(general, parquet);
  mkArrow(tavily, chromaStore);
  mkArrow(rag, chromaStore);

  // ======================================================
  // LAYER 4: STREAMLIT DASHBOARD
  // ======================================================
  const dashSec = mkSection(med, "Streamlit Dashboard (ui/streamlit_app.py)", 100, 7400, 7800, 600, SEC_GREEN);

  const liveTab = await mkShape(dashSec,
    "🫀 Live Monitor\n\nReal-time vitals display\nAgent decision logs\nSSE streaming",
    400, 150, 900, 300, LGREEN);

  const analyticsTab = await mkShape(dashSec,
    "📊 DuckDB Analytics\n\nHistorical vitals queries\nSeverity distribution\nCustom SQL on Parquet",
    1700, 150, 900, 300, LPURPLE);

  const archTab = await mkShape(dashSec,
    "🏗️ Architecture Tab\n\nSystem design explanation\nKey design decisions",
    3000, 150, 900, 300, LBLUE);

  mkArrow(parquet, liveTab);
  mkArrow(parquet, analyticsTab);

  // ======================================================
  // DONE
  // ======================================================
  figma.viewport.scrollAndZoomIntoView([med]);
  figma.notify("✅ Medical Agent diagram created! " + med.children.length + " elements");
})();
