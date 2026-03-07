"use client";

import type { PortfolioData, RendimientoData } from "@/lib/google-sheets";

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="card-unergy !p-4 text-center">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="font-display text-2xl font-bold text-unergy-deep-purple">
        {value}
      </p>
      <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
    </div>
  );
}

const fmtB = (n: number | null): string => {
  if (n === null) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `COP ${(n / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `COP ${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `COP ${(n / 1e6).toFixed(1)}M`;
  return `COP ${n.toLocaleString("es-CO")}`;
};

const fmtUsd = (n: number | null): string => {
  if (n === null) return "—";
  if (Math.abs(n) >= 1e6) return `USD ${(n / 1e6).toFixed(1)}M`;
  return `USD ${n.toLocaleString("en-US")}`;
};

const fmtPct = (n: number | null): string =>
  n !== null ? `${n.toFixed(1)}%` : "—";

const fmtNum = (n: number | null): string =>
  n !== null ? n.toLocaleString("es-CO") : "—";

export function PortfolioSection({
  portfolio,
  rendimiento,
}: {
  portfolio: PortfolioData;
  rendimiento: RendimientoData;
}) {
  return (
    <div className="space-y-6">
      {/* Portafolio de Inversión */}
      <div>
        <h3 className="font-display text-sm font-semibold text-unergy-cream mb-3">
          Portafolio de Inversión
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard
            label="Valor Portafolio"
            value={portfolio.valorPortafolio ? fmtB(portfolio.valorPortafolio) : fmtUsd(portfolio.valorPortafolioUsd)}
            sub="Total bajo gestión"
          />
          <KpiCard
            label="ROI Proyectado"
            value={fmtPct(portfolio.roiProyectado)}
            sub="Retorno esperado"
          />
          <KpiCard
            label="Generación Anual"
            value={fmtNum(portfolio.generacionAnual)}
            sub="kWh / año"
          />
          <KpiCard
            label="CO₂ Evitado"
            value={fmtNum(portfolio.co2Evitado)}
            sub="Toneladas / año"
          />
        </div>
      </div>

      {/* Rendimiento Financiero */}
      <div>
        <h3 className="font-display text-sm font-semibold text-unergy-cream mb-3">
          Rendimiento Financiero
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard
            label="TIR Real"
            value={fmtPct(rendimiento.tirReal)}
            sub="Tasa interna retorno"
          />
          <KpiCard
            label="Payback"
            value={rendimiento.payback !== null ? `${rendimiento.payback}` : "—"}
            sub="Años recuperación"
          />
          <KpiCard
            label="Factor Planta"
            value={fmtPct(rendimiento.factorPlanta)}
            sub="Promedio portafolio"
          />
          <KpiCard
            label="Margen EBITDA"
            value={fmtPct(rendimiento.margenEbitda)}
            sub="Eficiencia operativa"
          />
        </div>
      </div>
    </div>
  );
}
