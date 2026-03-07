"use client";

import { useState, useTransition, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { Amortizacion } from "@/types/database";
import { addAmortizacionRow, deleteAmortizacionRow } from "./actions";

const fmtCurrency = (v: number) =>
  v.toLocaleString("es-CO", { style: "decimal", maximumFractionDigits: 0 });

export function AmortizacionSection({
  amortizacion: initialData,
  deudaId,
  monto,
  canEdit,
}: {
  amortizacion: Amortizacion[];
  deudaId: string;
  monto: number;
  canEdit: boolean;
}) {
  const [rows, setRows] = useState(initialData);
  const [isPending, startTransition] = useTransition();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    fecha_pago: "",
    capital: "",
    intereses: "",
  });

  // Sort by date
  const sorted = useMemo(
    () => [...rows].sort((a, b) => a.fecha_pago.localeCompare(b.fecha_pago)),
    [rows]
  );

  // Calculate running balance
  const withBalance = useMemo(() => {
    let balance = monto;
    return sorted.map((r) => {
      balance -= r.capital;
      return { ...r, saldo: Math.max(0, balance) };
    });
  }, [sorted, monto]);

  const chartData = withBalance.map((r) => ({
    fecha: r.fecha_pago,
    Capital: r.capital,
    Intereses: r.intereses,
  }));

  // Totals
  const totalCapital = rows.reduce((s, r) => s + r.capital, 0);
  const totalIntereses = rows.reduce((s, r) => s + r.intereses, 0);
  const totalPagos = totalCapital + totalIntereses;

  const handleAdd = () => {
    if (!form.fecha_pago || !form.capital || !form.intereses) {
      setError("Todos los campos son requeridos");
      return;
    }
    setError(null);

    const data = {
      fecha_pago: form.fecha_pago,
      capital: parseFloat(form.capital),
      intereses: parseFloat(form.intereses),
    };

    startTransition(async () => {
      const result = await addAmortizacionRow(deudaId, data);
      if (result.success) {
        setShowForm(false);
        setForm({ fecha_pago: "", capital: "", intereses: "" });
        setRows((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            deuda_id: deudaId,
            ...data,
            total: data.capital + data.intereses,
          },
        ]);
      } else {
        setError(result.error);
      }
    });
  };

  const handleDelete = (id: string) => {
    setRows((prev) => prev.filter((r) => r.id !== id));
    startTransition(async () => {
      const result = await deleteAmortizacionRow(id);
      if (!result.success) {
        setRows(initialData);
        setError(result.error);
      }
    });
  };

  const inputClass =
    "text-xs border border-gray-300 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-unergy-purple w-full";

  return (
    <div>
      {/* Chart */}
      {sorted.length > 0 && (
        <div className="card-unergy mb-4 p-4">
          <h3 className="font-display text-sm font-semibold text-unergy-deep-purple mb-3">
            Calendario de Pagos
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="fecha" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number | undefined) => value != null ? fmtCurrency(value) : "—"}
              />
              <Legend />
              <Bar dataKey="Capital" stackId="a" fill="#915BD8" />
              <Bar dataKey="Intereses" stackId="a" fill="#d1d5db" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Summary */}
      {rows.length > 0 && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="card-unergy !p-3 text-center">
            <p className="text-xs text-gray-500">Monto Original</p>
            <p className="font-display font-bold text-unergy-deep-purple">{fmtCurrency(monto)}</p>
          </div>
          <div className="card-unergy !p-3 text-center">
            <p className="text-xs text-gray-500">Total Capital</p>
            <p className="font-display font-bold text-unergy-purple">{fmtCurrency(totalCapital)}</p>
          </div>
          <div className="card-unergy !p-3 text-center">
            <p className="text-xs text-gray-500">Total Intereses</p>
            <p className="font-display font-bold text-gray-600">{fmtCurrency(totalIntereses)}</p>
          </div>
          <div className="card-unergy !p-3 text-center">
            <p className="text-xs text-gray-500">Total Pagos</p>
            <p className="font-display font-bold text-unergy-deep-purple">{fmtCurrency(totalPagos)}</p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card-unergy">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-sm font-semibold text-unergy-deep-purple">
            Tabla de Amortizacion
          </h3>
          <span className="text-xs text-gray-400">{rows.length} pago(s)</span>
        </div>

        {error && (
          <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
            {error}
          </div>
        )}

        {rows.length === 0 && !showForm ? (
          <p className="text-sm text-gray-400 text-center py-6">
            No hay pagos registrados. Agrega pagos manualmente o importa desde CSV.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-unergy-deep-purple">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 pr-3 font-semibold">Fecha Pago</th>
                  <th className="pb-2 pr-3 font-semibold text-right">Capital</th>
                  <th className="pb-2 pr-3 font-semibold text-right">Intereses</th>
                  <th className="pb-2 pr-3 font-semibold text-right">Total</th>
                  <th className="pb-2 pr-3 font-semibold text-right">Saldo</th>
                  {canEdit && <th className="pb-2"></th>}
                </tr>
              </thead>
              <tbody>
                {withBalance.map((r) => (
                  <tr key={r.id} className="border-b border-gray-100 last:border-b-0">
                    <td className="py-2 pr-3 font-medium">
                      {new Date(r.fecha_pago + "T00:00:00").toLocaleDateString("es-CO")}
                    </td>
                    <td className="py-2 pr-3 text-right text-unergy-purple font-medium">
                      {fmtCurrency(r.capital)}
                    </td>
                    <td className="py-2 pr-3 text-right text-gray-600">
                      {fmtCurrency(r.intereses)}
                    </td>
                    <td className="py-2 pr-3 text-right font-semibold">
                      {fmtCurrency(r.total)}
                    </td>
                    <td className="py-2 pr-3 text-right text-gray-500">
                      {fmtCurrency(r.saldo)}
                    </td>
                    {canEdit && (
                      <td className="py-2">
                        <button
                          onClick={() => handleDelete(r.id)}
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
                <label className="text-xs text-gray-500">Fecha Pago *</label>
                <input
                  type="date"
                  value={form.fecha_pago}
                  onChange={(e) => setForm({ ...form, fecha_pago: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Capital *</label>
                <input
                  type="number"
                  value={form.capital}
                  onChange={(e) => setForm({ ...form, capital: e.target.value })}
                  placeholder="500000"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Intereses *</label>
                <input
                  type="number"
                  value={form.intereses}
                  onChange={(e) => setForm({ ...form, intereses: e.target.value })}
                  placeholder="150000"
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
                {isPending ? "Guardando..." : "Guardar Pago"}
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
            + Agregar pago
          </button>
        )}
      </div>
    </div>
  );
}
