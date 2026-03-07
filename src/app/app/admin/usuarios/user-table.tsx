"use client";

import { updateUserRole } from "./actions";
import { useTransition } from "react";

type Usuario = {
  id: string;
  email: string;
  nombre: string | null;
  rol: string;
  creado_en: string;
};

const roles = ["admin", "editor", "viewer", "pendiente"] as const;

const roleBadgeColors: Record<string, string> = {
  admin: "bg-unergy-purple text-white",
  editor: "bg-blue-100 text-blue-800",
  viewer: "bg-gray-100 text-gray-800",
  pendiente: "bg-yellow-100 text-yellow-800",
};

export function UserTable({
  usuarios,
  currentUserId,
}: {
  usuarios: Usuario[];
  currentUserId: string;
}) {
  const [isPending, startTransition] = useTransition();

  const handleRoleChange = (userId: string, newRole: string) => {
    startTransition(async () => {
      try {
        await updateUserRole(userId, newRole);
      } catch (err) {
        alert(err instanceof Error ? err.message : "Error al actualizar rol");
      }
    });
  };

  if (usuarios.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        No hay usuarios registrados.
      </p>
    );
  }

  return (
    <table className="w-full text-left text-unergy-deep-purple">
      <thead>
        <tr className="border-b border-gray-200">
          <th className="pb-3 font-semibold text-sm">Nombre</th>
          <th className="pb-3 font-semibold text-sm">Email</th>
          <th className="pb-3 font-semibold text-sm">Rol</th>
          <th className="pb-3 font-semibold text-sm">Registrado</th>
          <th className="pb-3 font-semibold text-sm">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {usuarios.map((u) => (
          <tr key={u.id} className="border-b border-gray-100 last:border-b-0">
            <td className="py-3 text-sm">{u.nombre || "—"}</td>
            <td className="py-3 text-sm text-gray-600">{u.email}</td>
            <td className="py-3">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                  roleBadgeColors[u.rol] || "bg-gray-100 text-gray-800"
                }`}
              >
                {u.rol}
              </span>
            </td>
            <td className="py-3 text-sm text-gray-500">
              {new Date(u.creado_en).toLocaleDateString("es-CO")}
            </td>
            <td className="py-3">
              {u.id !== currentUserId ? (
                <select
                  value={u.rol}
                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  disabled={isPending}
                  className="text-sm border border-gray-300 rounded-button px-2 py-1 bg-white disabled:opacity-50"
                >
                  {roles.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-xs text-gray-400 italic">
                  Tu cuenta
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
