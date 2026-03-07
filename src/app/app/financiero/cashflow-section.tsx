"use client";

import {
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from "recharts";
import type { CashFlowAnual } from "@/lib/google-sheets";

const fmtCOP = (v: number) => {
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
  return v.toLocaleString("es-CO");
};

export function CashFlowSection({ data }: { data: CashFlowAnual[] }) {
  if (data.length === 0) {
    return (
      <div className="card-unergy text-center py-8">
        <p className="text-sm text-gray-400">No hay datos de flujo de caja.</p>
      </div>
    );
  }

  // Limit to first 15 years for readability
  const chartData = data.slice(0, 15).map((d) => ({
    year: d.year.toString(),
    Ingresos: d.ingresos,
    Costos: -d.costos,
    CAPEX: d.capex > 0 ? -d.capex : 0,
    "Flujo Neto": d.flujoNeto,
  }));

  return (
    <div>
      <h3 className="font-display text-sm font-semibold text-unergy-cream mb-3">
        Flujo de Caja Consolidado
      </h3>
      <div className="card-unergy p-4">
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3d3350" />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 11, fill: "#a0a0a0" }}
              axisLine={{ stroke: "#3d3350" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#a0a0a0" }}
              tickFormatter={fmtCOP}
              axisLine={{ stroke: "#3d3350" }}
            />
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any, name: any) => [
                `COP ${fmtCOP(value ?? 0)}`,
                name,
              ]}
              contentStyle={{
                backgroundColor: "#2C2039",
                border: "1px solid #915BD8",
                borderRadius: "8px",
                color: "#FDFAF7",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#a0a0a0" }}
            />
            <Bar
              dataKey="Ingresos"
              stackId="stack"
              fill="#915BD8"
              radius={[2, 2, 0, 0]}
            />
            <Bar
              dataKey="Costos"
              stackId="stack"
              fill="#E74C3C"
              radius={[0, 0, 2, 2]}
            />
            <Bar
              dataKey="CAPEX"
              stackId="stack"
              fill="#F39C12"
              radius={[0, 0, 2, 2]}
            />
            <Line
              type="monotone"
              dataKey="Flujo Neto"
              stroke="#F6FF72"
              strokeWidth={2}
              dot={{ r: 3, fill: "#F6FF72" }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function DscrChartSection({
  data,
  covenantMin,
}: {
  data: { periodo: string; dscr: number | null }[];
  covenantMin: number | null;
}) {
  if (data.length === 0) {
    return (
      <div className="card-unergy text-center py-8">
        <p className="text-sm text-gray-400">No hay datos de DSCR del Sheet.</p>
      </div>
    );
  }

  // Limit to reasonable number of points
  const filtered = data.filter((d) => d.dscr !== null && d.dscr > 0);
  const chartData = filtered.slice(0, 60).map((d) => ({
    periodo: d.periodo,
    DSCR: d.dscr,
  }));

  const minLine = covenantMin || 1.2;

  return (
    <div>
      <h3 className="font-display text-sm font-semibold text-unergy-cream mb-3">
        Histórico DSCR
      </h3>
      <div className="card-unergy p-4">
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3d3350" />
            <XAxis
              dataKey="periodo"
              tick={{ fontSize: 9, fill: "#a0a0a0" }}
              interval={Math.floor(chartData.length / 12)}
              axisLine={{ stroke: "#3d3350" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#a0a0a0" }}
              domain={[0.8, "auto"]}
              axisLine={{ stroke: "#3d3350" }}
            />
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any) => [`${(value ?? 0).toFixed(2)}x`, "DSCR"]}
              contentStyle={{
                backgroundColor: "#2C2039",
                border: "1px solid #915BD8",
                borderRadius: "8px",
                color: "#FDFAF7",
              }}
            />
            <Line
              type="monotone"
              dataKey="DSCR"
              stroke="#915BD8"
              strokeWidth={2}
              dot={{ r: 2, fill: "#915BD8" }}
              connectNulls
            />
            {/* Covenant minimum reference line */}
            <Line
              dataKey={() => minLine}
              stroke="#E74C3C"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              dot={false}
              name={`Mínimo: ${minLine.toFixed(2)}x`}
              legendType="line"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AmortizacionChartSection({
  data,
}: {
  data: { year: number; principal: number; intereses: number; saldo: number }[];
}) {
  if (data.length === 0) return null;

  const chartData = data.map((d) => ({
    year: d.year.toString(),
    Capital: d.principal,
    Intereses: d.intereses,
  }));

  return (
    <div>
      <h3 className="font-display text-sm font-semibold text-unergy-cream mb-3">
        Calendario de Pagos (Amortización)
      </h3>
      <div className="card-unergy p-4">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3d3350" />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 11, fill: "#a0a0a0" }}
              axisLine={{ stroke: "#3d3350" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#a0a0a0" }}
              tickFormatter={fmtCOP}
              axisLine={{ stroke: "#3d3350" }}
            />
            <Tooltip
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(value: any, name: any) => [
                `COP ${fmtCOP(value ?? 0)}`,
                name,
              ]}
              contentStyle={{
                backgroundColor: "#2C2039",
                border: "1px solid #915BD8",
                borderRadius: "8px",
                color: "#FDFAF7",
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: "#a0a0a0" }} />
            <Bar dataKey="Capital" stackId="a" fill="#915BD8" />
            <Bar dataKey="Intereses" stackId="a" fill="#d1d5db" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
