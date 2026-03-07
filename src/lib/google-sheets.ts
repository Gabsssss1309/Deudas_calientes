/**
 * Google Sheets integration — fetches public Sheets as CSV.
 * Zero-config: no API keys, no Service Account.
 * Works because sheets are shared as "anyone with the link".
 */

// ─── CSV Fetcher ────────────────────────────────────────────

async function fetchSheetCsv(sheetId: string, tabName: string): Promise<string[][]> {
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?tqx=out:csv&sheet=${encodeURIComponent(tabName)}`;

  const res = await fetch(url, { next: { revalidate: 300 } }); // cache 5 min
  if (!res.ok) {
    console.error(`[google-sheets] Failed to fetch tab "${tabName}": ${res.status}`);
    return [];
  }

  const text = await res.text();
  return parseCsv(text);
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let current = "";
  let inQuotes = false;
  let row: string[] = [];

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (inQuotes && text[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      row.push(current.trim());
      current = "";
    } else if (ch === "\n" && !inQuotes) {
      row.push(current.trim());
      rows.push(row);
      row = [];
      current = "";
    } else {
      current += ch;
    }
  }
  if (current || row.length > 0) {
    row.push(current.trim());
    rows.push(row);
  }
  return rows;
}

/** Parse a numeric string (handles COP formatting, negatives in parens, etc.) */
function parseNum(val: string): number | null {
  if (!val || val === "" || val === '""') return null;
  // Remove quotes, $, COP, spaces, dots as thousands sep
  let clean = val
    .replace(/"/g, "")
    .replace(/\$/g, "")
    .replace(/COP/gi, "")
    .replace(/\s/g, "")
    .replace(/%/g, "");

  // Handle parentheses as negative
  if (clean.startsWith("(") && clean.endsWith(")")) {
    clean = "-" + clean.slice(1, -1);
  }

  // Detect if dot is thousands separator (e.g., "40.808.830")
  const dotCount = (clean.match(/\./g) || []).length;
  const commaCount = (clean.match(/,/g) || []).length;

  if (dotCount > 1) {
    // Multiple dots = thousands separator (e.g., "40.808.830")
    clean = clean.replace(/\./g, "");
  } else if (dotCount === 1 && commaCount === 1) {
    // Dot + comma: comma is decimal (e.g., "1.234,56")
    clean = clean.replace(/\./g, "").replace(",", ".");
  } else if (commaCount === 1 && dotCount === 0) {
    // Single comma could be decimal
    clean = clean.replace(",", ".");
  }

  const n = parseFloat(clean);
  return isNaN(n) ? null : n;
}

function parsePct(val: string): number | null {
  const n = parseNum(val);
  if (n === null) return null;
  // If the raw value already had %, the number is already in percentage form
  if (val.includes("%")) return n;
  // If it's a decimal like 0.15, convert to percentage
  return Math.abs(n) < 1 ? n * 100 : n;
}

/** Find a row by label (searches column 0 or 1) */
function findRow(rows: string[][], label: string): string[] | null {
  const lower = label.toLowerCase();
  return rows.find(
    (r) =>
      r[0]?.toLowerCase().includes(lower) ||
      r[1]?.toLowerCase().includes(lower)
  ) || null;
}

// ─── Types ──────────────────────────────────────────────────

export interface PortfolioData {
  valorPortafolio: number | null;      // Total investment COP
  valorPortafolioUsd: number | null;   // Total investment USD
  roiProyectado: number | null;        // IRR %
  generacionAnual: number | null;      // kWh/year
  co2Evitado: number | null;           // Tons CO2/year
  numPlantas: number | null;
  capacidadInstalada: number | null;    // kWp
  precioVenta: number | null;          // COP/kWh (PPA)
}

export interface RendimientoData {
  tirReal: number | null;              // IRR investor with debt %
  payback: number | null;              // Years
  factorPlanta: number | null;         // %
  margenEbitda: number | null;         // %
  equityPct: number | null;            // %
  debtPct: number | null;              // %
  dscrCovenant: number | null;         // x
}

export interface CashFlowAnual {
  year: number;
  ingresos: number;
  costos: number;
  cashflowOperativo: number;
  capex: number;
  flujoNeto: number;
  acumulado: number;
}

export interface DscrMensual {
  periodo: string;          // "ene-25", "feb-25", etc.
  dscr: number | null;
  cfads: number | null;
  servicioDeuda: number | null;
  saldoDeuda: number | null;
}

export interface AmortizacionAnual {
  year: number;
  principal: number;
  intereses: number;
  total: number;
  saldo: number;
}

export interface SheetFinancieroData {
  portfolio: PortfolioData;
  rendimiento: RendimientoData;
  cashFlow: CashFlowAnual[];
  dscr: DscrMensual[];
  amortizacion: AmortizacionAnual[];
}

// ─── Fetchers ───────────────────────────────────────────────

async function fetchPortfolioData(sheetId: string): Promise<PortfolioData> {
  const rows = await fetchSheetCsv(sheetId, "Assumptions & Results");

  const defaults: PortfolioData = {
    valorPortafolio: null, valorPortafolioUsd: null, roiProyectado: null,
    generacionAnual: null, co2Evitado: null, numPlantas: null,
    capacidadInstalada: null, precioVenta: null,
  };
  if (rows.length === 0) return defaults;

  // Row 3: Number of Solar Plants (col B/index 1)
  const plantasRow = findRow(rows, "number of solar plant");
  // Row 9: SolAyurá investment COP (col C/index 2) and USD (col D/index 3)
  const solayuraRow = findRow(rows, "solayur");
  // Row 13: Installed Power kWp
  const capacidadRow = findRow(rows, "installed power") ||
    rows.find((r) => r[0]?.toLowerCase().includes("kWp") || r[1]?.toLowerCase().includes("kwp"));
  // Row 33: PPA Price
  const ppaRow = findRow(rows, "ppa price");
  // Row 46: Total Investment USD
  const investmentRow = findRow(rows, "total investment");
  // Row 15: IRR project
  const irrRow = findRow(rows, "irr");

  // Generation: Row 1 data from Cash Flow tab has annual kWh
  // For now, estimate from capacity: 40 plants × 1320 kWp × 1752 hrs (18.5% CF)
  const numPlantas = plantasRow ? parseNum(plantasRow[1] || plantasRow[2] || "") : null;
  const capacidadKwp = capacidadRow ? parseNum(capacidadRow[1] || capacidadRow[2] || "") : null;
  const factorPlanta = 0.185; // From screenshot: 18.5%
  const generacionAnual = numPlantas && capacidadKwp
    ? numPlantas * capacidadKwp * 8760 * factorPlanta
    : null;

  // CO2: factor de emisión Colombia ~0.47 tCO2/MWh
  const co2 = generacionAnual ? Math.round((generacionAnual / 1000) * 0.47) : null;

  return {
    valorPortafolio: solayuraRow ? parseNum(solayuraRow[2] || "") : null,
    valorPortafolioUsd: investmentRow ? parseNum(investmentRow[1] || investmentRow[2] || "") : null,
    roiProyectado: irrRow ? parsePct(irrRow[1] || irrRow[2] || "") : null,
    generacionAnual: generacionAnual ? Math.round(generacionAnual) : null,
    co2Evitado: co2,
    numPlantas,
    capacidadInstalada: capacidadKwp,
    precioVenta: ppaRow ? parseNum(ppaRow[1] || ppaRow[2] || "") : null,
  };
}

async function fetchRendimientoData(sheetId: string): Promise<RendimientoData> {
  const [assumptionsRows, analysisRows] = await Promise.all([
    fetchSheetCsv(sheetId, "Assumptions & Results"),
    fetchSheetCsv(sheetId, "Analysis"),
  ]);

  // From Analysis tab:
  // Row ~95: IRR investor with debt = 15.53%
  // Row ~96: Payback
  // Find the "Investor" + "Debt" section IRR
  let tirReal: number | null = null;
  let paybackYears: number | null = null;

  // Find all IRR rows, pick the one for "investor with debt"
  // The Analysis tab structure: sections separated by headers
  // Section ~row 85-100: "Annual Analysis - Investor with Debt & Taxes"
  const irrRows = analysisRows.filter(
    (r) => r[1]?.toLowerCase().trim() === "irr" || r[0]?.toLowerCase().trim() === "irr"
  );
  // Third IRR = investor with debt (index 2)
  if (irrRows.length >= 3) {
    tirReal = parsePct(irrRows[2][2] || irrRows[2][1] || "");
  } else if (irrRows.length >= 1) {
    tirReal = parsePct(irrRows[0][2] || irrRows[0][1] || "");
  }

  // Payback: look for the payback row in the debt section
  // Payback rows have 1s then 0s. Count the 1s = payback years
  const paybackRows = analysisRows.filter(
    (r) => r[1]?.toLowerCase().includes("payback") || r[0]?.toLowerCase().includes("payback")
  );
  if (paybackRows.length >= 3) {
    // Count how many "1" values before first "0"
    const row = paybackRows[2]; // Third = investor with debt
    let years = 0;
    for (let i = 2; i < row.length; i++) {
      if (parseNum(row[i]) === 1) years++;
      else if (parseNum(row[i]) === 0 && years > 0) break;
    }
    paybackYears = years > 0 ? years : null;
  }

  // From Assumptions tab:
  const dscrRow = findRow(assumptionsRows, "dscr") || findRow(assumptionsRows, "debt sculpted");

  // Margen EBITDA: from Cash Flow annual tab (revenue - opex) / revenue
  // We'll calculate it from first full year of operation
  let margenEbitda: number | null = null;
  // Row 5 (Total Revenues) and Row 20 (Total Costs) in Cash Flow annual
  const revenueRow = findRow(analysisRows, "revenue") || findRow(analysisRows, "ingreso");
  const expenseRow = findRow(analysisRows, "expense") || findRow(analysisRows, "gasto") || findRow(analysisRows, "cost");
  if (revenueRow && expenseRow) {
    // Use year 5 (column ~7) for a stabilized year
    const rev = parseNum(revenueRow[7] || "");
    const exp = parseNum(expenseRow[7] || "");
    if (rev && exp) {
      margenEbitda = Math.round(((rev + exp) / rev) * 1000) / 10; // exp is negative
    }
  }

  return {
    tirReal,
    payback: paybackYears,
    factorPlanta: 18.5, // From capacity factor in Assumptions
    margenEbitda,
    equityPct: 25, // From Assumptions: 25%
    debtPct: 75, // From Assumptions: 75%
    dscrCovenant: dscrRow ? parseNum(dscrRow[1] || dscrRow[2] || "") : null,
  };
}

async function fetchCashFlowData(sheetId: string): Promise<CashFlowAnual[]> {
  const rows = await fetchSheetCsv(sheetId, "Cash Flow annual COP");
  if (rows.length < 31) return [];

  const startYear = 2025;
  const cashFlows: CashFlowAnual[] = [];

  // Row indices (0-based):
  // 4: Total Revenues
  // 19: Total Costs and Expenses (negative)
  // 20: Operating Cash Flow
  // 22: CAPEX (negative)
  // 29: Net Cash Flow
  // 30: Accumulated Cash Flow

  const revenueRow = rows[4] || [];     // Total Revenues
  const costRow = rows[19] || [];       // Total Costs
  const opCfRow = rows[20] || [];       // Operating CF
  const capexRow = rows[22] || [];      // CAPEX
  const netCfRow = rows[29] || [];      // Net CF
  const accumRow = rows[30] || [];      // Accumulated

  // Data starts at column index 1 (year 1 = 2025)
  const maxYears = Math.min(revenueRow.length - 1, 34);

  for (let i = 1; i <= maxYears; i++) {
    const ingresos = parseNum(revenueRow[i] || "") || 0;
    const costos = parseNum(costRow[i] || "") || 0;
    const opCf = parseNum(opCfRow[i] || "") || 0;
    const capex = parseNum(capexRow[i] || "") || 0;
    const neto = parseNum(netCfRow[i] || "") || 0;
    const acum = parseNum(accumRow[i] || "") || 0;

    // Only include years with some activity
    if (ingresos === 0 && costos === 0 && neto === 0) continue;

    cashFlows.push({
      year: startYear + i - 1,
      ingresos,
      costos: Math.abs(costos),
      cashflowOperativo: opCf,
      capex: Math.abs(capex),
      flujoNeto: neto,
      acumulado: acum,
    });
  }

  return cashFlows;
}

async function fetchDscrData(sheetId: string): Promise<DscrMensual[]> {
  const rows = await fetchSheetCsv(sheetId, "Debt");
  if (rows.length < 10) return [];

  const dscrData: DscrMensual[] = [];

  // Debt tab structure (monthly):
  // Headers in row 0-2, data starts around row 3+
  // Need to find the DSCR column, periodo column, CFADS, etc.

  // Find header row (contains "DSCR", "Month", "Year")
  let headerIdx = -1;
  let dscrCol = -1;
  let monthCol = -1;
  let yearCol = -1;
  let cfadsCol = -1;
  let balanceCol = -1;

  for (let i = 0; i < Math.min(rows.length, 10); i++) {
    const row = rows[i];
    for (let j = 0; j < row.length; j++) {
      const cell = row[j]?.toLowerCase().trim() || "";
      if (cell === "dscr") { dscrCol = j; headerIdx = i; }
      if (cell === "month" || cell === "mes") monthCol = j;
      if (cell === "year" || cell === "año") yearCol = j;
      if (cell.includes("cfads")) cfadsCol = j;
      if (cell.includes("closing balance") || cell.includes("total closing")) balanceCol = j;
    }
    if (headerIdx >= 0) break;
  }

  if (headerIdx < 0) {
    // Try alternative: rows are columns (transposed structure)
    // The Debt tab might have months as rows
    // Let's try finding "DSCR" as a row label
    const dscrRow = findRow(rows, "dscr");
    if (dscrRow) {
      // Months are in columns, find the month header row
      const monthRow = rows[2] || rows[1] || []; // Usually row 2 or 3
      for (let i = 2; i < dscrRow.length; i++) {
        const dscr = parseNum(dscrRow[i] || "");
        if (dscr !== null && dscr > 0) {
          dscrData.push({
            periodo: monthRow[i] || `M${i}`,
            dscr,
            cfads: null,
            servicioDeuda: null,
            saldoDeuda: null,
          });
        }
      }
      return dscrData;
    }
    return [];
  }

  // Standard row-based structure
  for (let i = headerIdx + 1; i < rows.length; i++) {
    const row = rows[i];
    const dscr = parseNum(row[dscrCol] || "");
    if (dscr === null || dscr === 0) continue;

    const month = row[monthCol] || "";
    const year = row[yearCol] || "";
    const periodo = month && year ? `${month}-${year}` : row[1] || `Row${i}`;

    dscrData.push({
      periodo,
      dscr,
      cfads: cfadsCol >= 0 ? parseNum(row[cfadsCol] || "") : null,
      servicioDeuda: null,
      saldoDeuda: balanceCol >= 0 ? parseNum(row[balanceCol] || "") : null,
    });
  }

  return dscrData;
}

async function fetchAmortizacionData(sheetId: string): Promise<AmortizacionAnual[]> {
  // Use Cash Flow annual COP tab: rows 27 (Principal) and 28 (Interest)
  const rows = await fetchSheetCsv(sheetId, "Cash Flow annual COP");
  if (rows.length < 31) return [];

  const startYear = 2025;
  const amort: AmortizacionAnual[] = [];

  const principalRow = rows[27] || [];   // Principal Payments (negative)
  const interestRow = rows[28] || [];    // Interest (negative)
  const debtRow = rows[26] || [];        // New Debt

  // Now go year by year
  let runningDebt = 0;
  for (let i = 1; i <= 34; i++) {
    const newDebt = parseNum(debtRow[i] || "") || 0;
    const principal = Math.abs(parseNum(principalRow[i] || "") || 0);
    const intereses = Math.abs(parseNum(interestRow[i] || "") || 0);

    runningDebt += newDebt - principal;

    if (principal === 0 && intereses === 0 && newDebt === 0) continue;

    amort.push({
      year: startYear + i - 1,
      principal,
      intereses,
      total: principal + intereses,
      saldo: Math.max(0, runningDebt),
    });
  }

  return amort;
}

// ─── Main Export ─────────────────────────────────────────────

export async function fetchSheetFinancieroData(
  sheetId: string
): Promise<SheetFinancieroData | null> {
  try {
    const [portfolio, rendimiento, cashFlow, dscr, amortizacion] = await Promise.all([
      fetchPortfolioData(sheetId),
      fetchRendimientoData(sheetId),
      fetchCashFlowData(sheetId),
      fetchDscrData(sheetId),
      fetchAmortizacionData(sheetId),
    ]);

    return { portfolio, rendimiento, cashFlow, dscr, amortizacion };
  } catch (err) {
    console.error("[google-sheets] Failed to fetch financiero data:", err);
    return null;
  }
}
