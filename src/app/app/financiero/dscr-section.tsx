"use client";

import { useState, useTransition } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { PeriodoDscr } from "@/types/database";
import { addDscrPeriod, deleteDscrPeriod } from "./actions";

const COVENANT_MIN = 1.2;

function dscrColor(val: number | null): string {
  if (val == null) return "text-gray-400";
  if (val >= 1.2) return "text-green-700";
  if (val >= 1.0) return "text-yellow-700";
  return "text-red-700";
}

function dscrBg(val: number | null): string {
  if (val == null) return "";
  if (val >= 1.2) return "bg-green-50";
  if (val >= 1.0) return "bg-yellow-50";
  return "bg-red-50";
}

const fmt = (v: number | null) =>
  v != null ? v.toLocaleString("es-CO", { maximumFractionDigits: 2 }) : "—";
const fmtCurrency = (v: number | null) =>
  v != null
    ? v.toLocaleString("es-CO", { style: "decimal", maximumFractionDigits: 0 })
    : "—";

export function DscrSection({
  periodos: initialPeriodos,
  deudaId,
  canEdit,
}: {
  periodos: PeriodoDscr[];
  deudaId: string;
  canEdit: boolean;
}) {
  const [periodos, setPeriodos] = useState(initialPeriodos);
  const [isPending, startTransition] = useTransition();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    periodo: "",
    dscr_real: "",
    dscr_proyectado: "",
    cashflow: "",
    servicio_deuda: "",
    ingresos_operacionales: "",
    gastos_operativos: "",
    comision_fiduciaria: "",
    saldo_dsra: "",
  });

  const parseNum = (s: string): number | null => {
    const n = parseFloat(s);
    return isNaN(n) ? null : n;
  };

  const handleAdd = () => {
    if (!form.periodo.trim()) {
      setError("El periodo es requerido");
      return;
    }
    setError(null);

    const data = {
      periodo: form.periodo.trim(),
      dscr_real: parseNum(form.dscr_real),
      dscr_proyectado: parseNum(form.dscr_proyectado),
      cashflow: parseNum(form.cashflow),
      servicio_deuda: parseNum(form.servicio_deuda),
      ingresos_operacionales: parseNum(form.ingresos_operacionales),
      gastos_operativos: parseNum(form.gastos_operativos),
      comision_fiduciaria: parseNum(form.comision_fiduciaria),
      saldo_dsra: parseNum(form.saldo_dsra),
    };

    startTransition(async () => {
      const result = await addDscrPeriod(deudaId, data);
      if (result.success) {
        setShowForm(false);
        setForm({
          periodo: "",
          dscr_real: "",
          dscr_proyectado: "",
          cashflow: "",
          servicio_deuda: "",
          ingresos_operacionales: "",
          gastos_operativos: "",
          comision_fiduciaria: "",
          saldo_dsra: "",
        });
        // Optimistic: add to local state (will revalidate on next load)
        setPeriodos((prev) => [
          ...prev,
          { id: crypto.randomUUID(), deuda_id: deudaId, creado_en: new Date().toISOString(), fuente_archivo_url: null, ...data },
        ]);
      } else {
        setError(result.error);
      }
    });
  };

  const handleDelete = (id: string) => {
    setPeriodos((prev) => prev.filter((p) => p.id !== id));
    startTransition(async () => {
      const result = await deleteDscrPeriod(id);
      if (!result.success) {
        setPeriodos(initialPeriodos);
        setError(result.error);
      }
    });
  };

  // Sort by periodo for chart
  const sorted = [...periodos].sort((a, b) =>
    a.periodo.localeCompare(b.periodo)
  );

  const chartData = sorted.map((p) => ({
    periodo: p.periodo,
    "DSCR Real": p.dscr_real,
    "DSCR Proyectado": p.dscr_proyectado,
  }));

  const inputClass =
    "text-xs border border-gray-300 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-unergy-purple w-full";

  return (
    <div>
      {/* Chart */}
      {sorted.length > 0 && (
        <div className="card-unergy mb-4 p-4">
          <h3 className="font-display text-sm font-semibold text-unergy-deep-purple mb-3">
            DSCR Real vs Proyectado
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="periodo" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, "auto"]} />
              <Tooltip />
              <Legend />
              <ReferenceLine
                y={COVENANT_MIN}
                stroke="#F85149"
                strokeDasharray="6 3"
                label={{ value: `Min ${COVENANT_MIN}x`, fill: "#F85149", fontSize: 11 }}
              />
              <Line
                type="monotone"
                dataKey="DSCR Real"
                stroke="#915BD8"
                strokeWidth={2}
                dot={{ r: 4 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="DSCR Proyectado"
                stroke="#9ca3af"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ r: 3 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="card-unergy">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-sm font-semibold text-unergy-deep-purple">
            Periodos DSCR
          </h3>
          <span className="text-xs text-gray-400">{periodos.length} periodo(s)</span>
        </div>

        {error && (
          <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
            {error}
          </div>
        )}

        {periodos.length === 0 && !showForm ? (
          <p className="text-sm text-gray-400 text-center py-6">
            No hay datos DSCR. Agrega periodos manualmente o importa desde CSV.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-unergy-deep-purple">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 pr-2 font-semibold">Periodo</th>
                  <th className="pb-2 pr-2 font-semibold">DSCR Real</th>
                  <th className="pb-2 pr-2 font-semibold">DSCR Proy.</th>
                  <th className="pb-2 pr-2 font-semibold">Cashflow</th>
                  <th className="pb-2 pr-2 font-semibold">Serv. Deuda</th>
                  <th className="pb-2 pr-2 font-semibold">Ingresos</th>
                  <th className="pb-2 pr-2 font-semibold">Gastos</th>
                  <th className="pb-2 pr-2 font-semibold">DSRA</th>
                  {canEdit && <th className="pb-2 font-semibold"></th>}
                </tr>
              </thead>
              <tbody>
                {sorted.map((p) => (
                  <tr key={p.id} className="border-b border-gray-100 last:border-b-0">
                    <td className="py-2 pr-2 font-medium">{p.periodo}</td>
                    <td className={`py-2 pr-2 font-semibold ${dscrColor(p.dscr_real)} ${dscrBg(p.dscr_real)}`}>
                      {fmt(p.dscr_real)}
                    </td>
                    <td className={`py-2 pr-2 ${dscrColor(p.dscr_proyectado)}`}>
                      {fmt(p.dscr_proyectado)}
                    </td>
                    <td className="py-2 pr-2 text-gray-600">{fmtCurrency(p.cashflow)}</td>
                    <td className="py-2 pr-2 text-gray-600">{fmtCurrency(p.servicio_deuda)}</td>
                    <td className="py-2 pr-2 text-gray-600">{fmtCurrency(p.ingresos_operacionales)}</td>
                    <td className="py-2 pr-2 text-gray-600">{fmtCurrency(p.gastos_operativos)}</td>
                    <td className="py-2 pr-2 text-gray-600">{fmtCurrency(p.saldo_dsra)}</td>
                    {canEdit && (
                      <td className="py-2">
                        <button
                          onClick={() => handleDelete(p.id)}
                          disabled={isPending}
                          className="text-red-400 hover:text-red-600 disabled:opacity-50"
                          title="Eliminar"
                        >
                          X
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Add form */}
        {canEdit && showForm && (
          <div className="mt-3 border-t border-gray-200 pt-3">
            <div className="grid grid-cols-3 gap-2 mb-2">
              <div>
                <label className="text-xs text-gray-500">Periodo *</label>
                <input
                  value={form.periodo}
                  onChange={(e) => setForm({ ...form, periodo: e.target.value })}
                  placeholder="2025-Q1"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">DSCR Real</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.dscr_real}
                  onChange={(e) => setForm({ ...form, dscr_real: e.target.value })}
                  placeholder="1.35"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">DSCR Proyectado</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.dscr_proyectado}
                  onChange={(e) => setForm({ ...form, dscr_proyectado: e.target.value })}
                  placeholder="1.40"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Cashflow</label>
                <input
                  type="number"
                  value={form.cashflow}
                  onChange={(e) => setForm({ ...form, cashflow: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Servicio Deuda</label>
                <input
                  type="number"
                  value={form.servicio_deuda}
                  onChange={(e) => setForm({ ...form, servicio_deuda: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Ingresos</label>
                <input
                  type="number"
                  value={form.ingresos_operacionales}
                  onChange={(e) => setForm({ ...form, ingresos_operacionales: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Gastos</label>
                <input
                  type="number"
                  value={form.gastos_operativos}
                  onChange={(e) => setForm({ ...form, gastos_operativos: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Comision Fiduciaria</label>
                <input
                  type="number"
                  value={form.comision_fiduciaria}
                  onChange={(e) => setForm({ ...form, comision_fiduciaria: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Saldo DSRA</label>
                <input
                  type="number"
                  value={form.saldo_dsra}
                  onChange={(e) => setForm({ ...form, saldo_dsra: e.target.value })}
                  className={inputClass}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleAdd}
                disabled={isPending}
                className="btn-primary text-xs !px-4 !py-2 disabled:opacity-50"
              >
                {isPending ? "Guardando..." : "Guardar Periodo"}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="btn-secondary text-xs !px-4 !py-2"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {canEdit && !showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="mt-3 text-xs text-unergy-purple hover:underline"
          >
            + Agregar periodo
          </button>
        )}
      </div>
    </div>
  );
}
