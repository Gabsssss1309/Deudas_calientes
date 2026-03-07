"use client";

import { useState, useTransition } from "react";

interface Props {
  type: "dscr" | "amortizacion";
  onImport: (rows: Record<string, unknown>[]) => Promise<{ success: boolean; error?: string }>;
}

function parseCsv(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = text.trim().split("\n");
  if (lines.length < 2) return { headers: [], rows: [] };

  // Detect separator (comma or semicolon)
  const sep = lines[0].includes(";") ? ";" : ",";

  const headers = lines[0].split(sep).map((h) => h.trim().replace(/^"|"$/g, ""));
  const rows = lines.slice(1).map((line) => {
    const vals = line.split(sep).map((v) => v.trim().replace(/^"|"$/g, ""));
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => {
      obj[h] = vals[i] || "";
    });
    return obj;
  });

  return { headers, rows };
}

const DSCR_COLUMNS = [
  "periodo",
  "dscr_real",
  "dscr_proyectado",
  "cashflow",
  "servicio_deuda",
  "ingresos_operacionales",
  "gastos_operativos",
  "comision_fiduciaria",
  "saldo_dsra",
];

const AMORT_COLUMNS = ["fecha_pago", "capital", "intereses"];

export function CsvImport({ type, onImport }: Props) {
  const [showImport, setShowImport] = useState(false);
  const [parsed, setParsed] = useState<Record<string, string>[] | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const expectedCols = type === "dscr" ? DSCR_COLUMNS : AMORT_COLUMNS;

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const { headers: h, rows } = parseCsv(text);
      if (rows.length === 0) {
        setError("El archivo no contiene datos");
        return;
      }
      setHeaders(h);
      setParsed(rows);
    };
    reader.readAsText(file);
  };

  const handleImport = () => {
    if (!parsed) return;
    setError(null);

    // Map to expected format
    const mapped = parsed.map((row) => {
      const obj: Record<string, unknown> = {};
      for (const col of expectedCols) {
        const val = row[col] ?? "";
        if (col === "periodo" || col === "fecha_pago") {
          obj[col] = val;
        } else {
          const num = parseFloat(val.replace(",", "."));
          obj[col] = isNaN(num) ? null : num;
        }
      }
      return obj;
    });

    startTransition(async () => {
      const result = await onImport(mapped);
      if (result.success) {
        setShowImport(false);
        setParsed(null);
        setHeaders([]);
      } else {
        setError(result.error || "Error al importar");
      }
    });
  };

  if (!showImport) {
    return (
      <button
        onClick={() => setShowImport(true)}
        className="text-xs text-unergy-purple hover:underline"
      >
        Importar CSV
      </button>
    );
  }

  return (
    <div className="card-unergy mt-4">
      <h4 className="font-display text-sm font-semibold text-unergy-deep-purple mb-2">
        Importar desde CSV
      </h4>
      <p className="text-xs text-gray-400 mb-3">
        El CSV debe tener estas columnas: <code className="bg-gray-100 px-1 rounded">{expectedCols.join(", ")}</code>
      </p>

      {error && (
        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
          {error}
        </div>
      )}

      <input
        type="file"
        accept=".csv,.txt"
        onChange={handleFile}
        className="text-xs text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-unergy-purple/10 file:text-unergy-purple hover:file:bg-unergy-purple/20 file:cursor-pointer mb-3"
      />

      {parsed && (
        <>
          <div className="overflow-x-auto max-h-48 mb-3 border border-gray-200 rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {headers.map((h) => (
                    <th key={h} className="px-2 py-1 font-semibold text-gray-600">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parsed.slice(0, 10).map((row, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    {headers.map((h) => (
                      <td key={h} className="px-2 py-1 text-gray-700">
                        {row[h]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 mb-3">
            Mostrando {Math.min(10, parsed.length)} de {parsed.length} filas
          </p>
        </>
      )}

      <div className="flex gap-2">
        {parsed && (
          <button
            onClick={handleImport}
            disabled={isPending}
            className="btn-primary text-xs !px-4 !py-2 disabled:opacity-50"
          >
            {isPending ? "Importando..." : `Importar ${parsed.length} filas`}
          </button>
        )}
        <button
          onClick={() => {
            setShowImport(false);
            setParsed(null);
            setHeaders([]);
            setError(null);
          }}
          className="btn-secondary text-xs !px-4 !py-2"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
