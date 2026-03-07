"use client";

import { useState } from "react";
import type { PeriodoDscr, Amortizacion, Deuda } from "@/types/database";
import type { SheetFinancieroData } from "@/lib/google-sheets";
import { DscrSection } from "./dscr-section";
import { AmortizacionSection } from "./amortizacion-section";
import { CsvImport } from "./csv-import";
import { PortfolioSection } from "./portfolio-section";
import {
  CashFlowSection,
  DscrChartSection,
  AmortizacionChartSection,
} from "./cashflow-section";
import { importDscrFromCsv, importAmortizacionFromCsv } from "./actions";

type DeudaWithData = {
  deuda: Deuda;
  periodos: PeriodoDscr[];
  amortizacion: Amortizacion[];
  sheetData: SheetFinancieroData | null;
};

export function FinancieroView({
  deudasData,
  canEdit,
}: {
  deudasData: DeudaWithData[];
  canEdit: boolean;
}) {
  const [selectedDeudaId, setSelectedDeudaId] = useState(
    deudasData.length > 0 ? deudasData[0].deuda.id : ""
  );

  const current = deudasData.find((d) => d.deuda.id === selectedDeudaId);
  const sheet = current?.sheetData;

  const handleDscrImport = async (rows: Record<string, unknown>[]) => {
    return importDscrFromCsv(
      selectedDeudaId,
      rows as Parameters<typeof importDscrFromCsv>[1]
    );
  };

  const handleAmortImport = async (rows: Record<string, unknown>[]) => {
    return importAmortizacionFromCsv(
      selectedDeudaId,
      rows as Parameters<typeof importAmortizacionFromCsv>[1]
    );
  };

  if (deudasData.length === 0) {
    return (
      <div className="card-unergy text-center py-12">
        <p className="text-gray-500 mb-2">No hay deudas registradas.</p>
        <p className="text-sm text-gray-400">
          Registra una deuda primero para agregar datos financieros.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Deuda selector — styled as tabs */}
      <div className="flex gap-1 mb-6 border-b border-unergy-purple/20">
        {deudasData.map(({ deuda }) => (
          <button
            key={deuda.id}
            onClick={() => setSelectedDeudaId(deuda.id)}
            className={`px-5 py-2.5 text-sm font-semibold transition-colors rounded-t-lg ${
              selectedDeudaId === deuda.id
                ? "text-unergy-cream border-b-2 border-unergy-yellow bg-unergy-purple/10"
                : "text-gray-400 hover:text-gray-300"
            }`}
          >
            {deuda.nombre}
          </button>
        ))}
      </div>

      {current && (
        <div className="space-y-8">
          {/* ─── Sheet-powered sections (if Sheet is configured) ─── */}
          {sheet && (
            <>
              {/* KPI Cards: Portafolio + Rendimiento */}
              <PortfolioSection
                portfolio={sheet.portfolio}
                rendimiento={sheet.rendimiento}
              />

              {/* Cash Flow Chart */}
              <CashFlowSection data={sheet.cashFlow} />

              {/* DSCR from Sheet */}
              <DscrChartSection
                data={sheet.dscr}
                covenantMin={sheet.rendimiento.dscrCovenant}
              />

              {/* Amortización from Sheet */}
              <AmortizacionChartSection data={sheet.amortizacion} />
            </>
          )}

          {/* ─── Supabase-powered sections (manual/CSV data) ─── */}
          {!sheet && (
            <>
              <DscrSection
                periodos={current.periodos}
                deudaId={current.deuda.id}
                canEdit={canEdit}
              />
              {canEdit && (
                <CsvImport type="dscr" onImport={handleDscrImport} />
              )}

              <AmortizacionSection
                amortizacion={current.amortizacion}
                deudaId={current.deuda.id}
                monto={current.deuda.monto}
                canEdit={canEdit}
              />
              {canEdit && (
                <CsvImport type="amortizacion" onImport={handleAmortImport} />
              )}
            </>
          )}

          {/* If Sheet is configured, also show raw Supabase data in collapsed section */}
          {sheet && (current.periodos.length > 0 || current.amortizacion.length > 0) && (
            <details className="mt-4">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                Ver datos manuales (Supabase)
              </summary>
              <div className="mt-3 space-y-4">
                <DscrSection
                  periodos={current.periodos}
                  deudaId={current.deuda.id}
                  canEdit={canEdit}
                />
                <AmortizacionSection
                  amortizacion={current.amortizacion}
                  deudaId={current.deuda.id}
                  monto={current.deuda.monto}
                  canEdit={canEdit}
                />
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
