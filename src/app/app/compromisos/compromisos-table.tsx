"use client";

import { useState, useMemo, useTransition } from "react";
import { updateCompromisoEstado } from "./actions";

type CompromisoRow = {
  id: string;
  clausula: string | null;
  descripcion: string;
  tipo_trigger: string | null;
  frecuencia: string | null;
  responsable: string | null;
  estado: string;
  notas: string | null;
  creado_en: string;
  deudas: { nombre: string } | null;
};

const estadoBadge: Record<string, string> = {
  pendiente: "bg-gray-100 text-gray-700",
  en_progreso: "bg-blue-100 text-blue-800",
  completado: "bg-green-100 text-green-800",
  vencido: "bg-red-100 text-red-800",
};

const estadoLabel: Record<string, string> = {
  pendiente: "Pendiente",
  en_progreso: "En progreso",
  completado: "Completado",
  vencido: "Vencido",
};

const responsableBadge: Record<string, string> = {
  Finanzas: "bg-blue-100 text-blue-800",
  Legal: "bg-purple-100 text-purple-800",
  "E&S": "bg-green-100 text-green-800",
  Seguros: "bg-orange-100 text-orange-800",
  Operaciones: "bg-yellow-100 text-yellow-800",
  Compliance: "bg-red-100 text-red-800",
  "Gerencia General": "bg-indigo-100 text-indigo-800",
};

const estados = ["pendiente", "en_progreso", "completado", "vencido"] as const;

export function CompromisosTable({
  compromisos: initialData,
  canEdit,
}: {
  compromisos: CompromisoRow[];
  canEdit: boolean;
}) {
  const [compromisos, setCompromisos] = useState(initialData);
  const [isPending, startTransition] = useTransition();

  // Filter state
  const [filterDeuda, setFilterDeuda] = useState("");
  const [filterResponsable, setFilterResponsable] = useState("");
  const [filterEstado, setFilterEstado] = useState("");
  const [filterTrigger, setFilterTrigger] = useState("");
  const [filterFrecuencia, setFilterFrecuencia] = useState("");
  const [search, setSearch] = useState("");

  // Derive unique values for filter dropdowns
  const uniqueDeudas = useMemo(
    () => Array.from(new Set(compromisos.map((c) => c.deudas?.nombre).filter(Boolean) as string[])).sort(),
    [compromisos]
  );
  const uniqueResponsables = useMemo(
    () => Array.from(new Set(compromisos.map((c) => c.responsable).filter(Boolean) as string[])).sort(),
    [compromisos]
  );
  const uniqueTriggers = useMemo(
    () => Array.from(new Set(compromisos.map((c) => c.tipo_trigger).filter(Boolean) as string[])).sort(),
    [compromisos]
  );
  const uniqueFrecuencias = useMemo(
    () => Array.from(new Set(compromisos.map((c) => c.frecuencia).filter(Boolean) as string[])).sort(),
    [compromisos]
  );

  // Filtered data
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return compromisos.filter((c) => {
      if (filterDeuda && c.deudas?.nombre !== filterDeuda) return false;
      if (filterResponsable && c.responsable !== filterResponsable) return false;
      if (filterEstado && c.estado !== filterEstado) return false;
      if (filterTrigger && c.tipo_trigger !== filterTrigger) return false;
      if (filterFrecuencia && c.frecuencia !== filterFrecuencia) return false;
      if (q) {
        const haystack = `${c.clausula || ""} ${c.descripcion} ${c.notas || ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [compromisos, filterDeuda, filterResponsable, filterEstado, filterTrigger, filterFrecuencia, search]);

  const hasFilters = filterDeuda || filterResponsable || filterEstado || filterTrigger || filterFrecuencia || search;

  const clearFilters = () => {
    setFilterDeuda("");
    setFilterResponsable("");
    setFilterEstado("");
    setFilterTrigger("");
    setFilterFrecuencia("");
    setSearch("");
  };

  const handleEstadoChange = (id: string, newEstado: string) => {
    // Optimistic update
    setCompromisos((prev) =>
      prev.map((c) => (c.id === id ? { ...c, estado: newEstado } : c))
    );

    startTransition(async () => {
      const result = await updateCompromisoEstado(id, newEstado);
      if (!result.success) {
        // Revert on error
        setCompromisos(initialData);
      }
    });
  };

  const selectClass =
    "text-xs border border-gray-300 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-unergy-purple";

  if (compromisos.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-2">No hay compromisos registrados aun.</p>
        <p className="text-sm text-gray-400">
          Sube un contrato en PDF para extraer compromisos automaticamente con IA.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select value={filterDeuda} onChange={(e) => setFilterDeuda(e.target.value)} className={selectClass}>
          <option value="">Todas las deudas</option>
          {uniqueDeudas.map((d) => (
            <option key={d} value={d!}>{d}</option>
          ))}
        </select>

        <select value={filterResponsable} onChange={(e) => setFilterResponsable(e.target.value)} className={selectClass}>
          <option value="">Todos los responsables</option>
          {uniqueResponsables.map((r) => (
            <option key={r} value={r!}>{r}</option>
          ))}
        </select>

        <select value={filterEstado} onChange={(e) => setFilterEstado(e.target.value)} className={selectClass}>
          <option value="">Todos los estados</option>
          {estados.map((e) => (
            <option key={e} value={e}>{estadoLabel[e]}</option>
          ))}
        </select>

        <select value={filterTrigger} onChange={(e) => setFilterTrigger(e.target.value)} className={selectClass}>
          <option value="">Todos los triggers</option>
          {uniqueTriggers.map((t) => (
            <option key={t} value={t!}>{t}</option>
          ))}
        </select>

        <select value={filterFrecuencia} onChange={(e) => setFilterFrecuencia(e.target.value)} className={selectClass}>
          <option value="">Todas las frecuencias</option>
          {uniqueFrecuencias.map((f) => (
            <option key={f} value={f!}>{f}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Buscar..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-xs border border-gray-300 rounded-lg px-3 py-1.5 bg-white text-gray-700 placeholder:text-gray-400 focus:outline-none focus:border-unergy-purple w-40"
        />

        {hasFilters && (
          <button onClick={clearFilters} className="text-xs text-unergy-purple hover:underline ml-1">
            Limpiar filtros
          </button>
        )}

        <span className="text-xs text-gray-400 ml-auto">
          {filtered.length === compromisos.length
            ? `${compromisos.length} compromisos`
            : `${filtered.length} de ${compromisos.length}`}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-unergy-deep-purple">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-3 pr-3 font-semibold text-xs">Deuda</th>
              <th className="pb-3 pr-3 font-semibold text-xs">Clausula</th>
              <th className="pb-3 pr-3 font-semibold text-xs min-w-[250px]">Descripcion</th>
              <th className="pb-3 pr-3 font-semibold text-xs">Trigger</th>
              <th className="pb-3 pr-3 font-semibold text-xs">Frecuencia</th>
              <th className="pb-3 pr-3 font-semibold text-xs">Responsable</th>
              <th className="pb-3 font-semibold text-xs">Estado</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => {
              const deudaNombre = c.deudas?.nombre ?? "—";
              const resp = c.responsable || "—";
              const respColor = responsableBadge[resp] || "bg-gray-100 text-gray-700";

              return (
                <tr key={c.id} className="border-b border-gray-100 last:border-b-0">
                  <td className="py-3 pr-3 text-sm font-medium">{deudaNombre}</td>
                  <td className="py-3 pr-3 text-sm text-gray-600">{c.clausula || "—"}</td>
                  <td className="py-3 pr-3 text-sm">{c.descripcion}</td>
                  <td className="py-3 pr-3 text-sm text-gray-600">{c.tipo_trigger || "—"}</td>
                  <td className="py-3 pr-3 text-sm text-gray-600">{c.frecuencia || "—"}</td>
                  <td className="py-3 pr-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium whitespace-nowrap ${respColor}`}>
                      {resp}
                    </span>
                  </td>
                  <td className="py-3">
                    {canEdit ? (
                      <select
                        value={c.estado}
                        onChange={(e) => handleEstadoChange(c.id, e.target.value)}
                        disabled={isPending}
                        className={`text-xs px-2 py-1 rounded-full font-medium border-0 cursor-pointer disabled:opacity-50 ${
                          estadoBadge[c.estado] || "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {estados.map((e) => (
                          <option key={e} value={e}>{estadoLabel[e]}</option>
                        ))}
                      </select>
                    ) : (
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                        estadoBadge[c.estado] || "bg-gray-100 text-gray-700"
                      }`}>
                        {estadoLabel[c.estado] || c.estado}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-sm text-gray-400 py-8">
          No hay compromisos que coincidan con los filtros.
        </p>
      )}
    </div>
  );
}
