"use client";

import type { ExtractedCompromiso } from "@/types/database";

interface Props {
  compromisos: ExtractedCompromiso[];
  onChange: (updated: ExtractedCompromiso[]) => void;
}

const triggerOptions = ["periodico", "evento", "solicitud"] as const;

const emptyRow: ExtractedCompromiso = {
  clausula: "",
  descripcion: "",
  tipo_trigger: null,
  plazo_dias: null,
  frecuencia: null,
  responsable_sugerido: "",
  notas: null,
};

export function ReviewTable({ compromisos, onChange }: Props) {
  const updateCell = (
    rowIndex: number,
    key: keyof ExtractedCompromiso,
    value: string | number | null
  ) => {
    const updated = compromisos.map((row, i) => {
      if (i !== rowIndex) return row;
      return { ...row, [key]: value };
    });
    onChange(updated);
  };

  const deleteRow = (rowIndex: number) => {
    onChange(compromisos.filter((_, i) => i !== rowIndex));
  };

  const addRow = () => {
    onChange([...compromisos, { ...emptyRow }]);
  };

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-unergy-deep-purple">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 font-semibold text-xs w-8">#</th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[100px]">
                Clausula
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[250px]">
                Descripcion
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[120px]">
                Trigger
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[80px]">
                Plazo (dias)
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[120px]">
                Frecuencia
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[150px]">
                Responsable
              </th>
              <th className="pb-2 pr-2 font-semibold text-xs min-w-[150px]">
                Notas
              </th>
              <th className="pb-2 font-semibold text-xs w-10"></th>
            </tr>
          </thead>
          <tbody>
            {compromisos.map((row, i) => (
              <tr
                key={i}
                className="border-b border-gray-100 last:border-b-0"
              >
                <td className="py-1.5 pr-2 text-xs text-gray-400">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.clausula}
                    onChange={(e) => updateCell(i, "clausula", e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <textarea
                    value={row.descripcion}
                    onChange={(e) =>
                      updateCell(i, "descripcion", e.target.value)
                    }
                    rows={2}
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple resize-y"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <select
                    value={row.tipo_trigger ?? ""}
                    onChange={(e) =>
                      updateCell(
                        i,
                        "tipo_trigger",
                        e.target.value || null
                      )
                    }
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple"
                  >
                    <option value="">—</option>
                    {triggerOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="number"
                    value={row.plazo_dias ?? ""}
                    onChange={(e) =>
                      updateCell(
                        i,
                        "plazo_dias",
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.frecuencia ?? ""}
                    onChange={(e) =>
                      updateCell(i, "frecuencia", e.target.value || null)
                    }
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.responsable_sugerido}
                    onChange={(e) =>
                      updateCell(i, "responsable_sugerido", e.target.value)
                    }
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <textarea
                    value={row.notas ?? ""}
                    onChange={(e) =>
                      updateCell(i, "notas", e.target.value || null)
                    }
                    rows={2}
                    className="w-full text-sm border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:border-unergy-purple resize-y"
                  />
                </td>
                <td className="py-1.5">
                  <button
                    type="button"
                    onClick={() => deleteRow(i)}
                    className="text-red-400 hover:text-red-600 transition-colors p-1"
                    title="Eliminar fila"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={addRow}
        className="mt-3 text-sm text-unergy-purple hover:text-unergy-purple/80 font-medium transition-colors"
      >
        + Agregar fila
      </button>
    </div>
  );
}
